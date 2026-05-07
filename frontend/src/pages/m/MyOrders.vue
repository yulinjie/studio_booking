<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showDialog, showSuccessToast, showFailToast, showLoadingToast, closeToast } from 'vant'
import dayjs from 'dayjs'
import api from '../../api/client'
import Icon from '../../components/Icon.vue'
import EmptyState from '../../components/EmptyState.vue'

const router = useRouter()
const orders = ref([])
const loading = ref(true)
const reuploadOrderId = ref(null)

async function load() {
  try { orders.value = await api.get('/me/orders') } finally { loading.value = false }
}

const STATUS_STYLE = {
  pending:   { bg: '#FAEEDE', color: '#A4836B', label: '审核中', icon: '⏳' },
  paid:      { bg: '#E0E8DC', color: '#6E7E63', label: '已通过', icon: '✓' },
  cancelled: { bg: '#F2DDD3', color: '#A4654E', label: '已驳回', icon: '✗' },
  refunded:  { bg: '#EEEAE2', color: '#9E9890', label: '已退款', icon: '↺' },
}

async function cancel(o) {
  try { await showDialog({ title: '取消订单？', message: '取消后该订单作废，可重新下单', showCancelButton: true }) } catch { return }
  try {
    await api.post(`/me/orders/${o.id}/cancel`)
    showSuccessToast('已取消')
    await load()
  } catch (e) { showFailToast(e.message) }
}

async function reuploadProof(o, file) {
  const f = file?.file || file
  const fd = new FormData()
  fd.append('file', f)
  showLoadingToast({ message: '上传中...', forbidClick: true, duration: 0 })
  try {
    const r = await fetch('/api/admin/upload', {
      method: 'POST',
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      body: fd,
    })
    const d = await r.json()
    if (!r.ok) throw new Error(d.detail || '上传失败')
    await api.patch(`/me/orders/${o.id}`, { payment_proof: d.url })
    closeToast()
    showSuccessToast('凭证已更新')
    reuploadOrderId.value = null
    await load()
  } catch (e) { closeToast(); showFailToast(e.message) }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <header class="topbar">
      <div class="back" @click="router.back()"><Icon name="chevron-left" :size="20" /></div>
      <div class="title-text">我的订单</div>
      <div class="back-spacer"></div>
    </header>

    <div v-if="loading" class="loading-state">加载中...</div>
    <EmptyState v-else-if="!orders.length" illust="bookmark" title="还没有订单" sub="去卡包页选张卡试试" />

    <div v-else class="list">
      <div v-for="o in orders" :key="o.id" class="o-card">
        <div class="status-stripe" :style="{ background: STATUS_STYLE[o.status]?.color || '#CCC' }"></div>
        <div class="o-body">
          <div class="o-row">
            <div class="o-name">{{ o.template_name }}</div>
            <div class="o-status" :style="{ background: STATUS_STYLE[o.status]?.bg, color: STATUS_STYLE[o.status]?.color }">
              {{ STATUS_STYLE[o.status]?.icon }} {{ STATUS_STYLE[o.status]?.label }}
            </div>
          </div>
          <div class="o-meta">
            <span>订单号 {{ o.order_no }}</span>
          </div>
          <div class="o-meta">
            <span>金额 <b>¥{{ (o.amount / 100).toFixed(2) }}</b></span>
            <span class="dot">·</span>
            <span>{{ dayjs(o.created_at).format('M-D HH:mm') }}</span>
          </div>

          <div v-if="o.payment_proof" class="proof-row">
            <span class="proof-label">付款凭证</span>
            <img :src="o.payment_proof" class="proof-thumb" @click="$event.target.classList.toggle('big')" />
          </div>

          <div v-if="o.status === 'cancelled' && o.reject_reason" class="reject-line">
            <Icon name="alert-circle" :size="12" /> 驳回原因：{{ o.reject_reason }}
          </div>

          <div v-if="o.status === 'pending'" class="o-actions">
            <van-uploader v-if="!o.payment_proof || reuploadOrderId === o.id"
                          :max-count="1" :after-read="(f) => reuploadProof(o, f)">
              <van-button size="mini" type="primary" plain round>
                <Icon name="image-plus" :size="11" /> {{ o.payment_proof ? '换张截图' : '上传截图' }}
              </van-button>
            </van-uploader>
            <van-button v-else size="mini" plain round @click="reuploadOrderId = o.id">
              <Icon name="refresh-cw" :size="11" /> 重传截图
            </van-button>
            <van-button size="mini" plain type="danger" round @click="cancel(o)">取消</van-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { min-height: 100vh; padding-bottom: 20px; }
.topbar {
  position: sticky; top: 0; z-index: 9;
  display: grid; grid-template-columns: 40px 1fr 40px; align-items: center;
  background: rgba(247, 243, 236, 0.92);
  backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
  padding: 12px 14px; border-bottom: 1px solid var(--ys-line);
}
.back { color: var(--ys-text); cursor: pointer; }
.title-text { text-align: center; font-size: 15px; letter-spacing: 1px; color: var(--ys-text); }

.list { padding: 16px; display: flex; flex-direction: column; gap: 10px; }
.loading-state { text-align: center; padding: 80px 0; color: var(--ys-text-muted); }

.o-card {
  background: var(--ys-bg-card);
  border-radius: var(--ys-radius);
  display: flex;
  overflow: hidden;
  box-shadow: var(--ys-shadow-sm);
  border: 1px solid var(--ys-line);
}
.status-stripe { width: 4px; flex: none; }
.o-body { flex: 1; padding: 14px; }
.o-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.o-name { font-size: 15px; font-weight: 500; color: var(--ys-text); }
.o-status { font-size: 11px; padding: 3px 10px; border-radius: 10px; letter-spacing: 0.5px; white-space: nowrap; }
.o-meta { font-size: 12px; color: var(--ys-text-muted); margin-top: 4px; display: flex; gap: 6px; align-items: center; }
.o-meta b { color: var(--ys-text); font-weight: 500; }
.dot { color: var(--ys-text-light); }

.proof-row { display: flex; align-items: center; gap: 8px; margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--ys-line); }
.proof-label { font-size: 11px; color: var(--ys-text-muted); }
.proof-thumb {
  width: 60px; height: 60px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid var(--ys-line);
  cursor: pointer;
  transition: all 0.2s;
}
.proof-thumb.big {
  position: fixed;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 90vw; height: auto; max-height: 80vh;
  z-index: 999;
  border: 4px solid white;
  box-shadow: var(--ys-shadow-lg);
}

.reject-line {
  font-size: 12px;
  color: var(--ys-danger);
  background: rgba(200, 146, 126, 0.1);
  padding: 6px 10px;
  border-radius: 6px;
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.o-actions { margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap; }
</style>
