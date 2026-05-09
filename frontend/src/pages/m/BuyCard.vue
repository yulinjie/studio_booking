<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showFailToast, showLoadingToast, closeToast, showSuccessToast } from 'vant'
import api from '../../api/client'
import Icon from '../../components/Icon.vue'
import { safeSrc } from '../../composables/security.js'

const router = useRouter()
const templates = ref([])
const studio = ref({})
const loading = ref(true)
const submitting = ref(false)

// 选购流程状态：browse | confirm | pay
const stage = ref('browse')
const selected = ref(null)
const proofUrl = ref('')
const orderId = ref(null)
const uploadedFiles = ref([])     // 修：之前在底部 module-scope，多实例会串

async function load() {
  try {
    const [t, s] = await Promise.all([
      api.get('/card-templates'),
      api.get('/studio/config'),
    ])
    templates.value = t
    studio.value = s
  } finally { loading.value = false }
}

const TYPE_LABEL = {
  times: '次卡', period: '期限卡', stored: '储值卡', package: '私教卡包',
}
const TYPE_COLOR = {
  times: { from: '#88958D', to: '#B5C4A7' },
  period: { from: '#A4836B', to: '#C8A48C' },
  stored: { from: '#7A6F62', to: '#C9BAA1' },
  package: { from: '#7E6A85', to: '#B7A8B8' },
}

function pickCard(t) {
  selected.value = t
  stage.value = 'confirm'
}

async function submitOrder() {
  if (!selected.value) return
  submitting.value = true
  try {
    const r = await api.post('/me/orders', { template_id: selected.value.id })
    if (!r?.id) {
      console.error('[BuyCard] 订单创建后返回数据异常', r)
      showFailToast('订单创建异常，请联系工作人员')
      return
    }
    orderId.value = r.id
    stage.value = 'pay'
  } catch (e) {
    console.error('[BuyCard] 订单创建失败', e)
    showFailToast(e.message || '创建订单失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

async function handleProofUpload(file) {
  // file 是 vant uploader 给的 { file, status, message }
  const f = file?.file || file
  if (!f) { showFailToast('未选中文件'); return }
  if (f.size > 3 * 1024 * 1024) { showFailToast('图片过大，请压缩到 3MB 以内'); return }

  const fd = new FormData()
  fd.append('file', f)
  showLoadingToast({ message: '上传中...', forbidClick: true, duration: 0 })

  // 30 秒超时（避免 toast 一直转圈）
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), 30000)
  try {
    const r = await fetch('/api/me/upload', {
      method: 'POST',
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      body: fd,
      signal: ctrl.signal,
    })
    clearTimeout(timer)
    const data = await r.json().catch(() => ({}))
    if (!r.ok) throw new Error(data.detail || `上传失败 (HTTP ${r.status})`)
    proofUrl.value = data.url
    closeToast()
    showSuccessToast('截图已上传')
  } catch (e) {
    clearTimeout(timer)
    closeToast()
    showFailToast(e.name === 'AbortError' ? '上传超时（30s），请检查网络后重试' : e.message)
    // 失败时清空 uploader 让用户能再试
    uploadedFiles.value = []
  }
}

async function submitProof() {
  if (!proofUrl.value) return showFailToast('先上传付款截图')
  submitting.value = true
  try {
    await api.patch(`/me/orders/${orderId.value}`, { payment_proof: proofUrl.value })
    showSuccessToast('已提交，等待审核')
    setTimeout(() => router.replace('/m/my-orders'), 1000)
  } catch (e) { showFailToast(e.message) } finally { submitting.value = false }
}

function back() {
  if (stage.value === 'pay') {
    // 已经创建了 pending 订单，提示
    if (proofUrl.value) {
      stage.value = 'confirm'
    } else {
      showFailToast('订单已创建，去"我的订单"上传截图')
      router.replace('/m/my-orders')
    }
  } else if (stage.value === 'confirm') {
    stage.value = 'browse'
    selected.value = null
  } else {
    router.back()
  }
}

const total = computed(() => selected.value ? (selected.value.price / 100).toFixed(2) : '0')

onMounted(load)
</script>

<template>
  <div class="page">
    <header class="topbar">
      <div class="back" @click="back"><Icon name="chevron-left" :size="20" /></div>
      <div class="title-text">
        {{ stage === 'browse' ? '选择卡种' : stage === 'confirm' ? '确认订单' : '完成付款' }}
      </div>
      <div class="back-spacer"></div>
    </header>

    <!-- 阶段 1: 浏览 -->
    <div v-if="stage === 'browse'" class="content">
      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="!templates.length" class="empty-tip">
        暂无卡种，请联系前台
      </div>
      <div v-else class="card-list">
        <div
v-for="t in templates" :key="t.id" class="card-item"
             :style="{ background: `linear-gradient(135deg, ${TYPE_COLOR[t.type]?.from || '#88958D'} 0%, ${TYPE_COLOR[t.type]?.to || '#B5C4A7'} 100%)` }"
             @click="pickCard(t)">
          <div class="ci-top">
            <span class="ci-type">{{ TYPE_LABEL[t.type] }}</span>
            <Icon name="chevron-right" :size="16" color="rgba(255,255,255,0.7)" />
          </div>
          <div class="ci-name">{{ t.name }}</div>
          <div class="ci-price"><span class="cur">¥</span>{{ (t.price / 100).toFixed(0) }}</div>
          <div class="ci-bot">
            <span v-if="t.initial_credits">{{ t.initial_credits }} 次</span>
            <span v-if="t.initial_balance">余额 ¥{{ (t.initial_balance/100).toFixed(0) }}</span>
            <span v-if="t.valid_days">· {{ t.valid_days }} 天有效</span>
            <span v-if="!t.valid_days">· 永久</span>
          </div>
          <div v-if="t.description" class="ci-desc">{{ t.description }}</div>
        </div>
      </div>
    </div>

    <!-- 阶段 2: 确认下单 -->
    <div v-else-if="stage === 'confirm'" class="content">
      <div class="confirm-card">
        <div class="cc-row"><span>卡名</span><b>{{ selected.name }}</b></div>
        <div class="cc-row"><span>类型</span><span>{{ TYPE_LABEL[selected.type] }}</span></div>
        <div v-if="selected.initial_credits" class="cc-row"><span>初始次数</span><span>{{ selected.initial_credits }} 次</span></div>
        <div v-if="selected.initial_balance" class="cc-row"><span>初始余额</span><span>¥{{ (selected.initial_balance/100).toFixed(2) }}</span></div>
        <div v-if="selected.valid_days" class="cc-row"><span>有效期</span><span>{{ selected.valid_days }} 天</span></div>
        <div class="cc-row cc-total"><span>应付</span><b class="price">¥{{ total }}</b></div>
      </div>

      <p v-if="selected.description" class="desc">{{ selected.description }}</p>

      <div class="bot-bar">
        <van-button block type="primary" round :loading="submitting" @click="submitOrder">下一步：去付款</van-button>
        <p class="rule-tip">点击下一步将创建订单，下一步扫码付款 + 上传截图</p>
      </div>
    </div>

    <!-- 阶段 3: 付款 -->
    <div v-else-if="stage === 'pay'" class="content">
      <div class="pay-amount">
        <div class="pa-label">应付金额</div>
        <div class="pa-num"><span class="cur">¥</span>{{ total }}</div>
      </div>

      <div class="qr-block">
        <div v-if="safeSrc(studio.payment_qr)" class="qr-frame">
          <img :src="safeSrc(studio.payment_qr)" />
        </div>
        <div v-else class="qr-frame qr-empty">
          <Icon name="qr-code" :size="48" color="#C5BFB6" :stroke="1.5" />
          <p>工作室还没设置收款码<br>请联系前台扫他们的码付款</p>
        </div>
        <p v-if="studio.payment_note" class="payment-note">{{ studio.payment_note }}</p>
      </div>

      <div class="upload-block">
        <p class="ub-title">付款后请上传截图</p>
        <van-uploader v-model="uploadedFiles" :max-count="1" :after-read="handleProofUpload" />
        <img v-if="safeSrc(proofUrl)" :src="safeSrc(proofUrl)" class="proof-preview" />
      </div>

      <div class="bot-bar">
        <van-button block type="primary" round :loading="submitting" :disabled="!proofUrl" @click="submitProof">
          {{ proofUrl ? '提交订单' : '请先上传截图' }}
        </van-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { padding-bottom: 24px; min-height: 100vh; }

.topbar {
  position: sticky;
  top: 0;
  z-index: 9;
  display: grid;
  grid-template-columns: 40px 1fr 40px;
  align-items: center;
  background: rgba(247, 243, 236, 0.92);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  padding: 12px 14px;
  border-bottom: 1px solid var(--ys-line);
}
.back { color: var(--ys-text); cursor: pointer; }
.title-text { text-align: center; font-size: 15px; letter-spacing: 1px; color: var(--ys-text); }

.content { padding: 16px; }
.loading-state, .empty-tip { text-align: center; padding: 80px 20px; color: var(--ys-text-muted); }

.card-list { display: flex; flex-direction: column; gap: 12px; }
.card-item {
  border-radius: 18px;
  padding: 18px;
  color: white;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  box-shadow: var(--ys-shadow-sm);
  transition: transform 0.18s;
}
.card-item:active { transform: scale(0.98); }
.ci-top { display: flex; justify-content: space-between; align-items: center; }
.ci-type {
  font-size: 11px;
  letter-spacing: 2px;
  background: rgba(255, 255, 255, 0.2);
  padding: 3px 10px;
  border-radius: 10px;
}
.ci-name { font-size: 16px; letter-spacing: 1px; margin-top: 14px; opacity: 0.95; }
.ci-price { margin-top: 4px; font-size: 32px; font-weight: 300; letter-spacing: 1px; font-variant-numeric: tabular-nums; }
.ci-price .cur { font-size: 16px; opacity: 0.8; }
.ci-bot { font-size: 11px; opacity: 0.85; margin-top: 4px; }
.ci-bot span { margin-right: 4px; }
.ci-desc { font-size: 11px; opacity: 0.7; margin-top: 8px; line-height: 1.5; }

.confirm-card {
  background: var(--ys-bg-card);
  border-radius: var(--ys-radius);
  padding: 18px;
  box-shadow: var(--ys-shadow-sm);
}
.cc-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 10px 0;
  border-bottom: 1px solid var(--ys-line);
  font-size: 13px;
  color: var(--ys-text-soft);
}
.cc-row:last-child { border-bottom: 0; }
.cc-row b { color: var(--ys-text); font-weight: 500; }
.cc-total { padding-top: 14px; }
.cc-total .price { font-size: 24px; color: var(--ys-accent-deep); font-weight: 400; }

.desc { font-size: 12px; color: var(--ys-text-muted); margin: 14px 0; line-height: 1.7; }

.bot-bar { padding: 18px 0; }
.rule-tip { text-align: center; color: var(--ys-text-muted); font-size: 11px; margin: 8px 0 0; letter-spacing: 0.5px; }

.pay-amount { text-align: center; padding: 20px 0; }
.pa-label { font-size: 12px; color: var(--ys-text-muted); letter-spacing: 2px; }
.pa-num {
  font-size: 48px;
  font-weight: 200;
  color: var(--ys-text);
  margin-top: 4px;
  font-variant-numeric: tabular-nums;
  letter-spacing: 1px;
}
.pa-num .cur { font-size: 24px; opacity: 0.7; }

.qr-block { text-align: center; margin: 12px 0; }
.qr-frame {
  display: inline-block;
  background: white;
  padding: 14px;
  border-radius: var(--ys-radius);
  box-shadow: var(--ys-shadow-sm);
}
.qr-frame img { display: block; max-width: 240px; max-height: 320px; }
.qr-empty {
  background: var(--ys-bg-soft);
  color: var(--ys-text-muted);
  padding: 30px 24px;
  font-size: 13px;
  line-height: 1.6;
  border: 1px dashed var(--ys-border);
}
.qr-empty p { margin: 12px 0 0; }
.payment-note {
  margin: 14px auto 0;
  max-width: 320px;
  font-size: 12px;
  color: var(--ys-accent-deep);
  background: rgba(200, 164, 140, 0.1);
  padding: 8px 14px;
  border-radius: 8px;
  line-height: 1.6;
}

.upload-block { margin-top: 20px; }
.ub-title { font-size: 13px; color: var(--ys-text); font-weight: 500; margin-bottom: 10px; }
.proof-preview { display: none; }
</style>
