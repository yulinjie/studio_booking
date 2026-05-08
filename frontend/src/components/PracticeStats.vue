<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/client'

const stats = ref({ week: 0, month: 0, total: 0, days_since_last: null })
onMounted(async () => {
  try { stats.value = await api.get('/me/practice-stats') } catch (e) { console.warn('[PracticeStats] load failed:', e.message) }
})
</script>

<template>
  <div class="stats-card">
    <div class="stat">
      <div class="num">{{ stats.week }}</div>
      <div class="lbl">本周练习</div>
    </div>
    <div class="div"></div>
    <div class="stat">
      <div class="num">{{ stats.month }}</div>
      <div class="lbl">近 30 天</div>
    </div>
    <div class="div"></div>
    <div class="stat">
      <div class="num">{{ stats.total }}</div>
      <div class="lbl">累计上课</div>
    </div>
    <div v-if="stats.days_since_last !== null" class="last-tag">
      <template v-if="stats.days_since_last === 0">今天已练</template>
      <template v-else-if="stats.days_since_last === 1">昨天练过</template>
      <template v-else-if="stats.days_since_last < 7">{{ stats.days_since_last }} 天前</template>
      <template v-else>{{ stats.days_since_last }} 天没练习了，回来吧</template>
    </div>
  </div>
</template>

<style scoped>
.stats-card {
  display: flex;
  align-items: stretch;
  background: var(--ys-bg-card);
  border-radius: var(--ys-radius);
  padding: 16px 8px;
  position: relative;
  box-shadow: var(--ys-shadow-sm);
}
.stat { flex: 1; text-align: center; }
.num {
  font-size: 22px;
  font-weight: 400;
  color: var(--ys-primary-deep);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.5px;
}
.lbl {
  font-size: 11px;
  color: var(--ys-text-muted);
  letter-spacing: 1px;
  margin-top: 2px;
}
.div { width: 1px; background: var(--ys-line); margin: 8px 0; }
.last-tag {
  position: absolute;
  bottom: 6px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  color: var(--ys-accent-deep);
  background: rgba(200, 164, 140, 0.12);
  padding: 1px 8px;
  border-radius: 8px;
  letter-spacing: 0.5px;
  white-space: nowrap;
}
</style>
