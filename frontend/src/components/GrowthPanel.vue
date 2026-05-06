<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '../api/client'

const stats = ref(null)
const loading = ref(true)

async function load() {
  try { stats.value = await api.get('/me/growth') } finally { loading.value = false }
}

const progress = computed(() => {
  if (!stats.value?.next_badge) return 0
  return Math.min(100, Math.round(stats.value.next_badge.progress / stats.value.next_badge.threshold * 100))
})

onMounted(load)
</script>

<template>
  <div v-if="loading" class="g-loading"></div>
  <div v-else-if="stats" class="g-wrap">
    <!-- Hero 数字三连 -->
    <div class="hero">
      <div class="metric">
        <div class="m-value">{{ stats.total_attended }}</div>
        <div class="m-label">累计完成</div>
      </div>
      <div class="metric metric-accent">
        <div class="m-value">{{ stats.current_streak_weeks }}</div>
        <div class="m-label">连续周</div>
        <div v-if="stats.current_streak_weeks > 0" class="m-fire">🔥</div>
      </div>
      <div class="metric">
        <div class="m-value">{{ stats.practiced_hours }}</div>
        <div class="m-label">累计小时</div>
      </div>
    </div>

    <!-- 本周本月 -->
    <div class="period-line">
      <span>本周 <b>{{ stats.classes_this_week }}</b> 节</span>
      <span class="dot">·</span>
      <span>本月 <b>{{ stats.classes_this_month }}</b> 节</span>
    </div>

    <!-- 下一个徽章进度 -->
    <div v-if="stats.next_badge" class="next-badge">
      <div class="nb-row">
        <div class="nb-emoji">{{ stats.next_badge.emoji }}</div>
        <div class="nb-info">
          <div class="nb-name">距离 <b>{{ stats.next_badge.name }}</b> 还差 {{ stats.next_badge.threshold - stats.next_badge.progress }}</div>
          <div class="nb-desc">{{ stats.next_badge.description }}</div>
        </div>
      </div>
      <div class="nb-bar"><div class="nb-fill" :style="{ width: progress + '%' }"></div></div>
    </div>

    <!-- 徽章墙 -->
    <div class="badge-wall">
      <div v-for="b in stats.badges" :key="b.key"
           class="badge" :class="{ unlocked: b.unlocked }"
           :title="b.description">
        <div class="b-emoji">{{ b.emoji }}</div>
        <div class="b-name">{{ b.name }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.g-loading { height: 220px; background: var(--ys-bg-soft); border-radius: var(--ys-radius); animation: pulse 1.4s infinite; }
@keyframes pulse { 0%, 100% { opacity: 0.5 } 50% { opacity: 0.8 } }

.g-wrap {
  background: linear-gradient(135deg, #DDE5DC 0%, #EFEAE0 50%, #FAEEDE 100%);
  border-radius: var(--ys-radius-lg);
  padding: 18px;
  position: relative;
  overflow: hidden;
}

.hero {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 14px;
}
.metric {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-radius: var(--ys-radius);
  padding: 12px 8px;
  text-align: center;
  position: relative;
}
.metric-accent {
  background: rgba(200, 164, 140, 0.18);
  border: 1px solid rgba(200, 164, 140, 0.3);
}
.m-value {
  font-size: 26px;
  font-weight: 300;
  color: var(--ys-text);
  font-variant-numeric: tabular-nums;
  letter-spacing: 1px;
}
.m-label {
  font-size: 10px;
  color: var(--ys-text-muted);
  letter-spacing: 2px;
  margin-top: 2px;
}
.m-fire {
  position: absolute;
  top: 6px;
  right: 8px;
  font-size: 14px;
}

.period-line {
  text-align: center;
  font-size: 12px;
  color: var(--ys-text-soft);
  margin-bottom: 14px;
}
.period-line b { color: var(--ys-text); font-weight: 500; margin: 0 2px; }
.period-line .dot { margin: 0 6px; color: var(--ys-text-light); }

.next-badge {
  background: rgba(255, 255, 255, 0.5);
  border-radius: var(--ys-radius);
  padding: 12px 14px;
  margin-bottom: 14px;
}
.nb-row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.nb-emoji { font-size: 28px; }
.nb-info { flex: 1; }
.nb-name { font-size: 13px; color: var(--ys-text); }
.nb-name b { font-weight: 500; color: var(--ys-accent-deep); }
.nb-desc { font-size: 11px; color: var(--ys-text-muted); margin-top: 2px; }
.nb-bar { height: 4px; background: rgba(63, 60, 58, 0.08); border-radius: 2px; overflow: hidden; }
.nb-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--ys-accent), var(--ys-primary));
  transition: width 0.5s;
}

.badge-wall {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
}
.badge {
  background: rgba(255, 255, 255, 0.4);
  border-radius: 8px;
  padding: 8px 4px;
  text-align: center;
  opacity: 0.4;
  transition: all 0.2s;
}
.badge.unlocked { opacity: 1; background: rgba(255, 255, 255, 0.8); }
.b-emoji { font-size: 22px; line-height: 1; }
.b-name { font-size: 9px; color: var(--ys-text-soft); margin-top: 4px; letter-spacing: 0.5px; }
</style>
