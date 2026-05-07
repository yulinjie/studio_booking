<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import api from '../../api/client'

const orders = ref([])
const members = ref({})
const loading = ref(false)
const previewUrl = ref('')

async function load() {
  loading.value = true
  try {
    orders.value = await api.get('/admin/orders/pending')
    if (orders.value.length) {
      const m = await api.get('/admin/members', { params: { size: 500 } })
      members.value = Object.fromEntries(m.items.map(u => [u.id, u]))
    }
  } finally { loading.value = false }
}

const memberName = (id) => members.value[id]?.name || `#${id}`
const memberPhone = (id) => members.value[id]?.phone || ''

async function approve(o) {
  try {
    await ElMessageBox.confirm(
      `确认通过 ${memberName(o.member_id)} 的"${o.template_name}"购卡订单？\n实收 ¥${(o.amount/100).toFixed(2)}，将自动开卡。`,
      '通过审核', { type: 'success' },
    )
  } catch { return }
  try {
    await api.post(`/admin/orders/${o.id}/approve`, { method: 'wechat_qr' })
    ElMessage.success(`已通过，卡已开给 ${memberName(o.member_id)}`)
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

async function reject(o) {
  try {
    const { value } = await ElMessageBox.prompt(
      `驳回 ${memberName(o.member_id)} 的"${o.template_name}"购卡订单？请填驳回原因（会显示给会员）`,
      '驳回审核',
      { inputType: 'textarea', inputPlaceholder: '如：截图无效 / 金额对不上 / 其他' },
    )
    await api.post(`/admin/orders/${o.id}/reject`, { reason: value })
    ElMessage.success('已驳回')
    await load()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e?.message || '操作失败')
  }
}

const fen2yuan = (n) => (n / 100).toFixed(2)

onMounted(load)
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h2>购卡订单审核</h2>
        <div class="sub">{{ orders.length }} 笔待审核</div>
      </div>
      <el-button @click="load" :loading="loading">刷新</el-button>
    </div>

    <el-card v-loading="loading">
      <div v-if="!orders.length" class="empty">
        <div class="empty-icon">✓</div>
        <div class="empty-text">没有待审核订单</div>
        <div class="empty-sub">会员自助购卡的订单会出现在这里</div>
      </div>

      <div v-else class="orders-grid">
        <div v-for="o in orders" :key="o.id" class="order-card">
          <div class="o-head">
            <div class="o-info">
              <div class="o-member">{{ memberName(o.member_id) }} <span class="phone">{{ memberPhone(o.member_id) }}</span></div>
              <div class="o-meta">{{ o.order_no }} · {{ dayjs(o.created_at).format('M-D HH:mm') }}</div>
            </div>
            <div class="o-amount">¥{{ fen2yuan(o.amount) }}</div>
          </div>

          <div class="o-template">
            <div class="t-name">{{ o.template_name }}</div>
          </div>

          <div class="o-proof">
            <div class="proof-label">付款凭证</div>
            <div v-if="o.payment_proof" class="proof-img" @click="previewUrl = o.payment_proof">
              <img :src="o.payment_proof" />
              <div class="proof-hint">点击放大</div>
            </div>
            <div v-else class="proof-empty">⚠ 会员还没上传截图</div>
          </div>

          <div class="o-actions">
            <el-button type="success" @click="approve(o)" :disabled="!o.payment_proof">
              ✓ 通过 → 开卡
            </el-button>
            <el-button type="danger" plain @click="reject(o)">✗ 驳回</el-button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 截图预览 -->
    <el-dialog v-model="previewUrl" :title="false" width="80%" :show-close="true" align-center>
      <img v-if="previewUrl" :src="previewUrl" style="width: 100%; display: block" />
    </el-dialog>

    <el-alert type="info" show-icon :closable="false" style="margin-top: 16px">
      流程：会员在 H5"卡包→购卡"自助下单 → 上传付款截图 → 你在这里看截图 → 通过后系统自动开卡 + 发流水。<br>
      要让会员能买到卡，记得先在「设置」上传<b>收款二维码</b>。
    </el-alert>
  </div>
</template>

<style scoped>
.page-head { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 16px; }
.page-head h2 { margin: 0; font-size: 22px; font-weight: 500; letter-spacing: 1px; }
.sub { color: var(--ys-text-muted); font-size: 13px; margin-top: 4px; }

.empty { text-align: center; padding: 60px 20px; color: var(--ys-text-muted); }
.empty-icon { font-size: 48px; color: var(--ys-success); }
.empty-text { font-size: 15px; margin-top: 12px; letter-spacing: 1px; }
.empty-sub { font-size: 12px; color: var(--ys-text-light); margin-top: 4px; }

.orders-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}
.order-card {
  background: var(--ys-bg-card);
  border: 1px solid var(--ys-line);
  border-radius: var(--ys-radius);
  padding: 16px;
  box-shadow: var(--ys-shadow-sm);
}
.o-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.o-member { font-size: 15px; color: var(--ys-text); font-weight: 500; }
.o-member .phone { font-size: 12px; color: var(--ys-text-muted); margin-left: 6px; font-weight: 400; }
.o-meta { font-size: 11px; color: var(--ys-text-muted); margin-top: 2px; letter-spacing: 0.5px; }
.o-amount { font-size: 22px; color: var(--ys-accent-deep); font-weight: 400; font-variant-numeric: tabular-nums; }

.o-template { margin: 12px 0; padding: 10px 12px; background: var(--ys-bg-soft); border-radius: 6px; }
.t-name { font-size: 13px; color: var(--ys-text); }

.o-proof { margin: 12px 0; }
.proof-label { font-size: 11px; color: var(--ys-text-muted); letter-spacing: 1px; margin-bottom: 6px; }
.proof-img {
  position: relative;
  cursor: zoom-in;
  background: var(--ys-bg-soft);
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--ys-line);
}
.proof-img img { display: block; width: 100%; max-height: 220px; object-fit: contain; background: #fff; }
.proof-hint {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  padding: 4px 8px;
  background: rgba(63, 60, 58, 0.6);
  color: white;
  font-size: 11px;
  text-align: center;
}
.proof-empty {
  background: rgba(217, 185, 143, 0.18);
  color: var(--ys-warning);
  padding: 16px;
  text-align: center;
  font-size: 13px;
  border-radius: 6px;
}

.o-actions { display: flex; gap: 8px; margin-top: 12px; }
.o-actions .el-button { flex: 1; }
</style>
