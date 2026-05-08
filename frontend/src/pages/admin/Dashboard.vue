<script setup>
import { ref, onMounted, useTemplateRef, nextTick } from 'vue'
import api from '../../api/client'
import dayjs from 'dayjs'
import * as echarts from 'echarts/core'
import { LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, TitleComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([LineChart, BarChart, GridComponent, TooltipComponent, TitleComponent, LegendComponent, CanvasRenderer])

const todaySessions = ref([])
const memberCount = ref(0)
const newMemberCount = ref(0)
const activeCardCount = ref(0)
const todayBookings = ref(0)
const todayAttended = ref(0)
const monthRevenue = ref(0)

const trendRef = useTemplateRef('trendChart')
const courseRef = useTemplateRef('courseChart')

async function load() {
  // 当日课表
  const start = dayjs().startOf('day').toISOString()
  const end = dayjs().endOf('day').toISOString()
  todaySessions.value = await api.get('/sessions', { params: { start, end } })

  // KPI
  const m = await api.get('/admin/members', { params: { role: 'member', size: 1 } })
  memberCount.value = m.total
  const cards = await api.get('/admin/cards', { params: { status: 'active' } })
  activeCardCount.value = cards.length
  todayBookings.value = todaySessions.value.reduce((s, c) => s + c.booked_count, 0)

  // 近 7 天预约趋势 + 课程分布 — 通过 bookings 接口分析
  const since = dayjs().subtract(6, 'day').startOf('day')
  const sessionsRange = await api.get('/sessions', {
    params: {
      start: since.toISOString(),
      end: dayjs().endOf('day').toISOString(),
    },
  })

  // 趋势：近 7 天每天的 booked_count
  const dayBuckets = {}
  for (let i = 0; i < 7; i++) {
    dayBuckets[since.add(i, 'day').format('MM-DD')] = 0
  }
  for (const s of sessionsRange) {
    const k = dayjs(s.start_at).format('MM-DD')
    if (k in dayBuckets) dayBuckets[k] += s.booked_count
  }

  // 月营收 — 近 30 天 paid 订单
  try {
    const orders = await api.get('/admin/orders', { params: { status: 'paid' } })
    const since30 = dayjs().subtract(30, 'day')
    monthRevenue.value = orders
      .filter(o => o.paid_at && dayjs(o.paid_at).isAfter(since30))
      .reduce((s, o) => s + (o.paid_amount || 0), 0)
  } catch (e) { console.warn('[Dashboard] revenue load failed:', e.message) }

  // 新增会员（近 30 天）
  newMemberCount.value = (m.items || []).filter(u => dayjs(u.created_at).isAfter(dayjs().subtract(30, 'day'))).length

  // 已到课（近 7 天）
  try {
    const allBookings = await api.get('/admin/bookings')
    todayAttended.value = allBookings.filter(b =>
      b.checked_in_at && dayjs(b.checked_in_at).format('YYYY-MM-DD') === dayjs().format('YYYY-MM-DD')
    ).length
  } catch (e) { console.warn('[Dashboard] bookings load failed:', e.message) }

  await nextTick()
  drawTrend(Object.keys(dayBuckets), Object.values(dayBuckets))
  drawCourseDist(sessionsRange)
}

function drawTrend(labels, data) {
  if (!trendRef.value) return
  const chart = echarts.init(trendRef.value)
  chart.setOption({
    grid: { top: 30, right: 16, bottom: 28, left: 36 },
    tooltip: { trigger: 'axis', backgroundColor: '#fff', borderColor: '#E2DCCF', textStyle: { color: '#3F3C3A' } },
    xAxis: {
      type: 'category', data: labels,
      axisLine: { lineStyle: { color: '#D8D2C5' } },
      axisLabel: { color: '#9E9890', fontSize: 11 },
    },
    yAxis: {
      type: 'value', minInterval: 1,
      splitLine: { lineStyle: { color: '#EFEAE0' } },
      axisLabel: { color: '#9E9890', fontSize: 11 },
    },
    series: [{
      data,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color: '#88958D', width: 2 },
      itemStyle: { color: '#88958D' },
      areaStyle: {
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
          { offset: 0, color: 'rgba(136, 149, 141, 0.25)' },
          { offset: 1, color: 'rgba(136, 149, 141, 0.02)' },
        ]},
      },
    }],
  })
  window.addEventListener('resize', () => chart.resize())
}

function drawCourseDist(sessionsRange) {
  if (!courseRef.value) return
  const byCourse = {}
  for (const s of sessionsRange) {
    byCourse[s.course_id] = (byCourse[s.course_id] || 0) + s.booked_count
  }
  api.get('/admin/courses').then(courses => {
    const items = courses.map(c => ({ name: c.name, value: byCourse[c.id] || 0 })).sort((a,b) => b.value - a.value).slice(0, 6)
    const chart = echarts.init(courseRef.value)
    chart.setOption({
      grid: { top: 20, right: 16, bottom: 28, left: 80 },
      tooltip: { trigger: 'axis', backgroundColor: '#fff', borderColor: '#E2DCCF', textStyle: { color: '#3F3C3A' } },
      xAxis: { type: 'value', splitLine: { lineStyle: { color: '#EFEAE0' } }, axisLabel: { color: '#9E9890', fontSize: 11 } },
      yAxis: {
        type: 'category',
        data: items.map(i => i.name),
        axisLine: { lineStyle: { color: '#D8D2C5' } },
        axisLabel: { color: '#6B6660', fontSize: 12 },
      },
      series: [{
        type: 'bar',
        data: items.map(i => i.value),
        barWidth: 14,
        itemStyle: {
          color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [
            { offset: 0, color: '#B5C4A7' }, { offset: 1, color: '#88958D' },
          ]},
          borderRadius: [0, 6, 6, 0],
        },
      }],
    })
    window.addEventListener('resize', () => chart.resize())
  })
}

onMounted(load)
</script>

<template>
  <div class="dashboard">
    <div class="page-head">
      <div>
        <h2>晨光好</h2>
        <div class="sub">{{ dayjs().format('YYYY 年 M 月 D 日 dddd') }} · 云舍今日</div>
      </div>
    </div>

    <!-- KPI -->
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-label">会员总数</div>
        <div class="kpi-value">{{ memberCount }}</div>
        <div class="kpi-trend">近 30 天 +{{ newMemberCount }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">在用会员卡</div>
        <div class="kpi-value">{{ activeCardCount }}</div>
        <div class="kpi-trend">活跃资产</div>
      </div>
      <div class="kpi-card kpi-accent">
        <div class="kpi-label">今日预约</div>
        <div class="kpi-value">{{ todayBookings }}</div>
        <div class="kpi-trend">已签到 {{ todayAttended }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">近 30 日营收</div>
        <div class="kpi-value">¥{{ (monthRevenue/100).toFixed(0) }}</div>
        <div class="kpi-trend">含线下收款</div>
      </div>
    </div>

    <!-- 图表行 -->
    <el-row :gutter="16" style="margin-top: 20px">
      <el-col :span="14">
        <div class="ys-card chart-card">
          <div class="card-header">
            <span class="card-title">近 7 天预约趋势</span>
            <span class="card-tag">每日预约人次</span>
          </div>
          <div ref="trendChart" class="chart"></div>
        </div>
      </el-col>
      <el-col :span="10">
        <div class="ys-card chart-card">
          <div class="card-header">
            <span class="card-title">热门课程 (近 7 天)</span>
            <span class="card-tag">按预约人次</span>
          </div>
          <div ref="courseChart" class="chart"></div>
        </div>
      </el-col>
    </el-row>

    <!-- 今日课表 -->
    <div class="ys-card today-card" style="margin-top: 20px">
      <div class="card-header">
        <span class="card-title">今日课表</span>
        <router-link to="/admin/check-in" class="card-link">前往签到 ›</router-link>
      </div>
      <div v-if="!todaySessions.length" class="empty-mini">今天没有排课</div>
      <div v-else class="today-list">
        <div v-for="s in todaySessions" :key="s.id" class="t-row">
          <div class="t-time">{{ dayjs(s.start_at).format('HH:mm') }}</div>
          <div class="t-info">
            <div class="t-name">课程 #{{ s.course_id }} {{ s.room ? `· ${s.room}` : '' }}</div>
            <div class="t-meta">
              <span :class="{ 'is-full': s.booked_count >= s.capacity }">
                {{ s.booked_count }} / {{ s.capacity }} 人
              </span>
              · {{ s.status === 'finished' ? '已结束' : (s.status === 'cancelled' ? '已取消' : '进行中') }}
            </div>
          </div>
          <router-link :to="`/admin/check-in?sid=${s.id}`" class="t-action">›</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard { max-width: 1400px; }
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 20px;
}
.page-head h2 {
  margin: 0;
  font-size: 26px;
  font-weight: 400;
  letter-spacing: 2px;
}
.sub { color: var(--ys-text-muted); margin-top: 4px; font-size: 13px; }

.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.kpi-card {
  background: var(--ys-bg-card);
  border: 1px solid var(--ys-line);
  border-radius: var(--ys-radius);
  padding: 18px 20px;
  position: relative;
  overflow: hidden;
}
.kpi-card::before {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 2px;
  background: linear-gradient(90deg, var(--ys-primary), transparent);
  opacity: 0.5;
}
.kpi-label {
  font-size: 12px;
  color: var(--ys-text-muted);
  letter-spacing: 2px;
}
.kpi-value {
  font-size: 32px;
  font-weight: 300;
  color: var(--ys-text);
  margin: 8px 0 4px;
  letter-spacing: 1px;
  font-variant-numeric: tabular-nums;
}
.kpi-trend {
  font-size: 11px;
  color: var(--ys-text-muted);
  letter-spacing: 1px;
}
.kpi-accent {
  background: linear-gradient(135deg, var(--ys-primary-bg) 0%, var(--ys-bg-card) 100%);
}
.kpi-accent::before { background: linear-gradient(90deg, var(--ys-primary-deep), transparent); opacity: 0.8; }

.chart-card { padding: 16px 18px; }
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
}
.card-title { font-size: 14px; font-weight: 500; letter-spacing: 1px; color: var(--ys-text); }
.card-tag { font-size: 11px; color: var(--ys-text-muted); letter-spacing: 1px; }
.card-link {
  font-size: 12px;
  color: var(--ys-primary-deep);
  text-decoration: none;
  letter-spacing: 1px;
}
.chart { height: 220px; }

.today-card { padding: 16px 18px; }
.empty-mini {
  text-align: center;
  padding: 30px;
  color: var(--ys-text-muted);
  font-size: 13px;
  letter-spacing: 2px;
}
.today-list {
  display: flex;
  flex-direction: column;
}
.t-row {
  display: grid;
  grid-template-columns: 70px 1fr 30px;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--ys-line);
}
.t-row:last-child { border-bottom: 0; }
.t-time { font-size: 18px; font-weight: 400; color: var(--ys-text); font-variant-numeric: tabular-nums; }
.t-name { font-size: 14px; color: var(--ys-text); }
.t-meta { font-size: 12px; color: var(--ys-text-muted); margin-top: 2px; }
.is-full { color: var(--ys-danger); }
.t-action {
  text-align: center;
  font-size: 18px;
  color: var(--ys-text-light);
  text-decoration: none;
}
.t-action:hover { color: var(--ys-primary); }
</style>
