<script setup>
import { ref, onMounted } from 'vue'
import api from '../../api/client'
import dayjs from 'dayjs'
import EmptyState from '../../components/EmptyState.vue'
import Icon from '../../components/Icon.vue'

const tab = ref('unused')
const list = ref([])
async function load() {
  list.value = await api.get('/me/coupons', { params: { status: tab.value } })
}
onMounted(load)

const TYPE_TXT = { discount: '满减券', percent: '折扣券', cash: '现金券', free_class: '体验课' }
function valueText(c) {
  if (c.type === 'discount') return `¥${(c.value/100).toFixed(0)}`
  if (c.type === 'percent') return `${c.value}折`
  if (c.type === 'cash') return `¥${(c.value/100).toFixed(0)}`
  if (c.type === 'free_class') return `${c.value} 节`
  return c.value
}
</script>

<template>
  <div class="page">
    <header class="header">
      <h2>我的优惠券</h2>
      <p class="sub">{{ list.length }} 张</p>
    </header>

    <van-tabs v-model:active="tab" @change="load" line-width="32">
      <van-tab title="可用" name="unused" />
      <van-tab title="已用" name="used" />
      <van-tab title="过期" name="expired" />
    </van-tabs>

    <EmptyState v-if="!list.length" illust="bookmark"
      :title="tab === 'unused' ? '还没领到优惠券' : '没有相关券'"
      sub="到店或参加活动可获得优惠券" />

    <div v-else class="list">
      <div v-for="c in list" :key="c.id" class="coupon" :class="`status-${c.status}`">
        <div class="left">
          <div class="value">{{ valueText(c) }}</div>
          <div class="cond" v-if="c.min_amount > 0">满 ¥{{ (c.min_amount/100).toFixed(0) }}</div>
          <div class="type-tag">{{ TYPE_TXT[c.type] || c.type }}</div>
        </div>
        <div class="middle"></div>
        <div class="right">
          <div class="name">{{ c.name }}</div>
          <div class="till" v-if="c.valid_until">
            <Icon name="clock" :size="11" />
            <span>{{ dayjs(c.valid_until).format('YYYY-MM-DD') }} 前</span>
          </div>
          <div class="status-stamp" v-if="c.status !== 'unused'">{{ c.status === 'used' ? '已使用' : '已过期' }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { padding: 0 0 16px; }
.header { padding: 22px 20px 6px; }
.header h2 { margin: 0; font-size: 22px; font-weight: 500; letter-spacing: 1px; }
.sub { color: var(--ys-text-muted); margin: 4px 0 0; font-size: 13px; }

.list { padding: 16px; display: flex; flex-direction: column; gap: 10px; }

.coupon {
  display: grid;
  grid-template-columns: 110px 12px 1fr;
  background: var(--ys-bg-card);
  border-radius: var(--ys-radius);
  overflow: hidden;
  box-shadow: var(--ys-shadow-sm);
  border: 1px solid var(--ys-line);
  position: relative;
}
.coupon.status-used, .coupon.status-expired { opacity: 0.55; }

.left {
  background: linear-gradient(135deg, #FAEEDE 0%, #C8A48C 100%);
  color: white;
  padding: 14px 8px;
  text-align: center;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
}
.value { font-size: 26px; font-weight: 300; letter-spacing: 1px; }
.cond { font-size: 10px; opacity: 0.85; letter-spacing: 1px; }
.type-tag {
  display: inline-block;
  margin-top: 4px;
  background: rgba(255,255,255,0.2);
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 10px;
  letter-spacing: 1px;
}

.middle {
  position: relative;
  background: var(--ys-bg-card);
}
.middle::before, .middle::after {
  content: '';
  position: absolute;
  width: 12px; height: 12px;
  border-radius: 50%;
  background: var(--ys-bg);
  left: 0; right: 0;
}
.middle::before { top: -6px; }
.middle::after { bottom: -6px; }

.right {
  padding: 14px 14px 14px 4px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.name { font-size: 14px; font-weight: 500; color: var(--ys-text); letter-spacing: 0.5px; }
.till {
  font-size: 11px;
  color: var(--ys-text-muted);
  margin-top: 4px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.status-stamp {
  position: absolute;
  right: 10px;
  bottom: 8px;
  border: 1.5px solid var(--ys-text-light);
  color: var(--ys-text-light);
  padding: 2px 8px;
  font-size: 11px;
  letter-spacing: 2px;
  border-radius: 4px;
  transform: rotate(-8deg);
}
</style>
