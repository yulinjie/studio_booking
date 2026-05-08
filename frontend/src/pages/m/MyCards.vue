<script setup>
import { ref, onMounted } from 'vue'
import api from '../../api/client'
import dayjs from 'dayjs'
import ListSkeleton from '../../components/ListSkeleton.vue'

const cards = ref([])
const txByCard = ref({})
const expanded = ref({})
const refreshing = ref(false)
const firstLoaded = ref(false)

async function load() {
  try { cards.value = await api.get('/me/cards') } finally { firstLoaded.value = true }
}

async function onRefresh() {
  refreshing.value = true
  try {
    txByCard.value = {} // 刷新时清掉本地展开的流水缓存
    await load()
  } finally { refreshing.value = false }
}

async function toggle(card) {
  expanded.value[card.id] = !expanded.value[card.id]
  if (expanded.value[card.id] && !txByCard.value[card.id]) {
    txByCard.value[card.id] = await api.get(`/me/cards/${card.id}/transactions`)
  }
}

const TYPE_GRAD = {
  times:   { from: '#88958D', to: '#B5C4A7', label: '次卡' },
  period:  { from: '#A4836B', to: '#C8A48C', label: '期限卡' },
  stored:  { from: '#7A6F62', to: '#C9BAA1', label: '储值卡' },
  package: { from: '#7E6A85', to: '#B7A8B8', label: '私教卡包' },
}

const STATUS_TEXT = {
  active: '可用', used_up: '已用完', expired: '已过期', frozen: '已冻结', refunded: '已退',
}

const TX_LABEL = {
  purchase: '购卡', deduct_book: '预约扣次', refund_cancel: '取消返还',
  deduct_no_show: '爽约扣次', topup: '充值', adjust: '调整', expire: '过期', card_refund: '整卡退款',
}

function daysLeft(card) {
  if (!card.valid_until) return null
  const d = dayjs(card.valid_until).diff(dayjs(), 'day')
  return d
}

onMounted(load)
</script>

<template>
  <div class="page">
    <header class="header">
      <div class="head-row">
        <div>
          <h2>我的卡包</h2>
          <p class="sub">{{ cards.length }} 张卡 · {{ cards.filter(c=>c.status==='active').length }} 张可用</p>
        </div>
        <van-button type="primary" round size="small" @click="$router.push('/m/buy-card')">+ 购卡</van-button>
      </div>
      <div class="orders-link" @click="$router.push('/m/my-orders')">📦 我的订单 ›</div>
    </header>

    <ListSkeleton v-if="!firstLoaded" :count="3" />

    <van-pull-refresh v-else v-model="refreshing" @refresh="onRefresh">
    <div v-if="!cards.length" class="empty">
      <div class="empty-icon">◇</div>
      <div class="empty-text">还没有卡</div>
      <div class="empty-sub">到工作室前台购卡</div>
    </div>

    <div v-else class="cards">
      <div v-for="c in cards" :key="c.id" class="card-wrap">
        <div
class="card-face" :class="`status-${c.status}`"
             :style="{ background: `linear-gradient(135deg, ${TYPE_GRAD[c.type]?.from} 0%, ${TYPE_GRAD[c.type]?.to} 100%)` }"
             @click="toggle(c)">
          <div class="face-top">
            <div class="card-type">{{ TYPE_GRAD[c.type]?.label || c.type }}</div>
            <div v-if="c.status !== 'active'" class="card-status">{{ STATUS_TEXT[c.status] }}</div>
          </div>
          <div class="card-name">{{ c.name }}</div>
          <div class="card-amount">
            <template v-if="c.type === 'stored'">
              <span class="cur">¥</span>
              <span class="num">{{ (c.remaining_balance / 100).toFixed(2) }}</span>
            </template>
            <template v-else-if="c.type === 'period'">
              <span class="num">不限</span><span class="unit"> 次</span>
            </template>
            <template v-else>
              <span class="num">{{ c.remaining_credits }}</span><span class="unit"> 次</span>
            </template>
          </div>
          <div class="card-bot">
            <span v-if="c.valid_until">
              至 {{ dayjs(c.valid_until).format('YYYY-MM-DD') }}
              <em v-if="daysLeft(c) !== null && daysLeft(c) >= 0 && daysLeft(c) < 30" class="warn">· 还剩 {{ daysLeft(c) }} 天</em>
            </span>
            <span v-else>永久有效</span>
            <span class="card-no">No.{{ String(c.id).padStart(4, '0') }}</span>
          </div>

          <!-- 装饰 -->
          <div class="deco-circle deco-1"></div>
          <div class="deco-circle deco-2"></div>
        </div>

        <div v-if="expanded[c.id]" class="tx-panel">
          <div class="tx-title">流水</div>
          <div v-if="!txByCard[c.id]?.length" class="tx-empty">无流水</div>
          <div v-for="tx in txByCard[c.id]" :key="tx.id" class="tx-item">
            <div class="tx-row1">
              <span class="tx-type">{{ TX_LABEL[tx.type] || tx.type }}</span>
              <span class="tx-delta" :class="{ pos: tx.credits_delta > 0 || tx.balance_delta > 0, neg: tx.credits_delta < 0 || tx.balance_delta < 0 }">
                <template v-if="tx.credits_delta">{{ tx.credits_delta > 0 ? '+' : '' }}{{ tx.credits_delta }} 次</template>
                <template v-else-if="tx.balance_delta">{{ tx.balance_delta > 0 ? '+' : '' }}¥{{ (tx.balance_delta/100).toFixed(2) }}</template>
                <template v-else>-</template>
              </span>
            </div>
            <div class="tx-row2">
              <span>{{ dayjs(tx.created_at).format('M-D HH:mm') }}</span>
              <span v-if="tx.note">· {{ tx.note }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    </van-pull-refresh>
  </div>
</template>

<style scoped>
.page { padding: 0 0 16px; }
.header { padding: 22px 20px 14px; }
.header h2 { margin: 0; font-size: 22px; font-weight: 500; letter-spacing: 1px; }
.sub { color: var(--ys-text-muted); margin: 4px 0 0; font-size: 13px; }
.head-row { display: flex; justify-content: space-between; align-items: flex-end; }
.orders-link {
  margin-top: 12px;
  font-size: 13px;
  color: var(--ys-primary-deep);
  letter-spacing: 0.5px;
  cursor: pointer;
}

.cards { padding: 0 16px; display: flex; flex-direction: column; gap: 16px; }

.card-wrap {
  border-radius: 18px;
  overflow: hidden;
  box-shadow: var(--ys-shadow);
}
.card-face {
  position: relative;
  padding: 18px 20px 16px;
  color: white;
  cursor: pointer;
  overflow: hidden;
  min-height: 168px;
  display: flex;
  flex-direction: column;
}
.card-face.status-frozen, .card-face.status-expired,
.card-face.status-used_up, .card-face.status-refunded { filter: saturate(0.4) brightness(0.9); }

.face-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  z-index: 1;
}
.card-type {
  font-size: 11px;
  letter-spacing: 3px;
  background: rgba(255,255,255,0.18);
  padding: 3px 10px;
  border-radius: 10px;
}
.card-status {
  font-size: 11px;
  background: rgba(0,0,0,0.18);
  padding: 3px 10px;
  border-radius: 10px;
  letter-spacing: 1px;
}
.card-name {
  font-size: 16px;
  letter-spacing: 1px;
  margin-top: 14px;
  position: relative; z-index: 1;
  opacity: 0.95;
}
.card-amount {
  margin-top: 8px;
  display: flex;
  align-items: baseline;
  gap: 4px;
  position: relative; z-index: 1;
}
.card-amount .cur { font-size: 16px; opacity: 0.85; }
.card-amount .num {
  font-size: 36px;
  font-weight: 300;
  letter-spacing: 1px;
  font-variant-numeric: tabular-nums;
}
.card-amount .unit { font-size: 13px; opacity: 0.85; }

.card-bot {
  margin-top: auto;
  padding-top: 14px;
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  opacity: 0.85;
  letter-spacing: 1px;
  position: relative; z-index: 1;
}
.card-bot .warn { color: #FFE9C2; font-style: normal; }
.card-no { font-variant-numeric: tabular-nums; opacity: 0.7; }

.deco-circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255,255,255,0.08);
}
.deco-1 { width: 140px; height: 140px; right: -40px; top: -40px; }
.deco-2 { width: 80px; height: 80px; right: 60px; bottom: -30px; background: rgba(255,255,255,0.05); }

.tx-panel {
  background: var(--ys-bg-card);
  padding: 14px 18px 10px;
  border-top: 1px dashed var(--ys-line);
}
.tx-title {
  font-size: 11px;
  color: var(--ys-text-muted);
  letter-spacing: 4px;
  margin-bottom: 8px;
}
.tx-empty {
  text-align: center;
  color: var(--ys-text-light);
  padding: 12px 0;
  font-size: 13px;
}
.tx-item {
  padding: 8px 0;
  border-bottom: 1px solid var(--ys-line);
}
.tx-item:last-child { border-bottom: 0; }
.tx-row1 {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--ys-text);
}
.tx-delta { font-variant-numeric: tabular-nums; }
.tx-delta.pos { color: var(--ys-success); }
.tx-delta.neg { color: var(--ys-danger); }
.tx-row2 {
  display: flex;
  gap: 6px;
  font-size: 11px;
  color: var(--ys-text-muted);
  margin-top: 2px;
}

.empty { text-align: center; padding: 80px 20px; color: var(--ys-text-muted); }
.empty-icon { font-size: 60px; color: var(--ys-text-light); font-weight: 100; line-height: 1; }
.empty-text { font-size: 14px; margin-top: 16px; letter-spacing: 1px; }
.empty-sub { font-size: 12px; color: var(--ys-text-light); margin-top: 4px; }
</style>
