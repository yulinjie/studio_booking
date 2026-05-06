<script setup>
import { ref, onMounted, useTemplateRef, nextTick, watch } from 'vue'
import api from '../../api/client'
import dayjs from 'dayjs'
import * as echarts from 'echarts/core'
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import Icon from '../../components/Icon.vue'

echarts.use([LineChart, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent, CanvasRenderer])

const days = ref(30)
const revenue = ref({ labels: [], data: [], total: 0 })
const attendance = ref({ total: 0, attended: 0, no_show: 0, cancelled: 0, rate: 0 })
const coachHours = ref({ items: [] })
const liability = ref({ active_cards: 0, by_type: {}, total_remaining_credits: 0, total_remaining_balance: 0 })
const growth = ref({ labels: [], new: [], cumulative: [] })

const revRef = useTemplateRef('revRef')
const attRef = useTemplateRef('attRef')
const grRef = useTemplateRef('grRef')
const chRef = useTemplateRef('chRef')

async function load() {
  const [rev, att, ch, lia, gr] = await Promise.all([
    api.get('/admin/reports/revenue', { params: { days: days.value } }),
    api.get('/admin/reports/attendance', { params: { days: days.value } }),
    api.get('/admin/reports/coach-hours', { params: { days: days.value } }),
    api.get('/admin/reports/card-liability'),
    api.get('/admin/reports/member-growth', { params: { days: Math.max(days.value, 60) } }),
  ])
  revenue.value = rev
  attendance.value = att
  coachHours.value = ch
  liability.value = lia
  growth.value = gr
  await nextTick()
  drawAll()
}

function drawAll() {
  // 营收
  if (revRef.value) {
    const c = echarts.init(revRef.value)
    c.setOption({
      grid: { top: 28, right: 18, bottom: 28, left: 56 },
      tooltip: { trigger: 'axis', valueFormatter: (v) => '¥' + (v/100).toFixed(0) },
      xAxis: { type: 'category', data: revenue.value.labels, axisLabel: { color: '#9E9890', fontSize: 11 } },
      yAxis: { type: 'value', axisLabel: { color: '#9E9890', fontSize: 11, formatter: (v) => v >= 100 ? '¥' + (v/100).toFixed(0) : v }, splitLine: { lineStyle: { color: '#EFEAE0' } } },
      series: [{
        type: 'bar', data: revenue.value.data,
        itemStyle: {
          color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
            { offset: 0, color: '#C8A48C' }, { offset: 1, color: '#FAEEDE' },
          ]}, borderRadius: [4, 4, 0, 0],
        },
        barWidth: '60%',
      }],
    })
    window.addEventListener('resize', () => c.resize())
  }
  // 出席率（饼）
  if (attRef.value) {
    const c = echarts.init(attRef.value)
    c.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0, textStyle: { color: '#6B6660', fontSize: 11 }, itemWidth: 10, itemHeight: 10 },
      series: [{
        type: 'pie',
        radius: ['50%', '72%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: false,
        label: { show: true, formatter: '{b}\n{d}%', fontSize: 11, color: '#6B6660' },
        data: [
          { value: attendance.value.attended,  name: '到课', itemStyle: { color: '#9DAD93' } },
          { value: attendance.value.no_show,   name: '爽约', itemStyle: { color: '#C8927E' } },
          { value: attendance.value.cancelled, name: '取消', itemStyle: { color: '#C5BFB6' } },
        ],
      }],
    })
    window.addEventListener('resize', () => c.resize())
  }
  // 会员增长
  if (grRef.value) {
    const c = echarts.init(grRef.value)
    c.setOption({
      grid: { top: 28, right: 18, bottom: 28, left: 36 },
      tooltip: { trigger: 'axis' },
      legend: { right: 18, top: 0, textStyle: { color: '#6B6660', fontSize: 11 } },
      xAxis: { type: 'category', data: growth.value.labels, axisLabel: { color: '#9E9890', fontSize: 10 } },
      yAxis: [
        { type: 'value', axisLabel: { color: '#9E9890', fontSize: 11 }, splitLine: { lineStyle: { color: '#EFEAE0' } } },
        { type: 'value', axisLabel: { color: '#9E9890', fontSize: 11 } },
      ],
      series: [
        { name: '新增', type: 'bar', data: growth.value.new, itemStyle: { color: '#C8A48C' }, barWidth: '40%' },
        { name: '累计', type: 'line', yAxisIndex: 1, data: growth.value.cumulative, smooth: true, symbol: 'none', lineStyle: { color: '#88958D', width: 2 } },
      ],
    })
    window.addEventListener('resize', () => c.resize())
  }
  // 教练课时
  if (chRef.value) {
    const items = coachHours.value.items.slice(0, 8)
    const c = echarts.init(chRef.value)
    c.setOption({
      grid: { top: 16, right: 28, bottom: 28, left: 80 },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'value', splitLine: { lineStyle: { color: '#EFEAE0' } }, axisLabel: { color: '#9E9890', fontSize: 11 } },
      yAxis: { type: 'category', data: items.map(i => i.name), axisLabel: { color: '#6B6660', fontSize: 12 } },
      series: [{
        type: 'bar', data: items.map(i => i.session_count), barWidth: 12,
        itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [
          { offset: 0, color: '#B5C4A7' }, { offset: 1, color: '#88958D' },
        ]}, borderRadius: [0, 4, 4, 0] },
      }],
    })
    window.addEventListener('resize', () => c.resize())
  }
}

watch(days, load)
onMounted(load)
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h2>报表中心</h2>
        <div class="sub">基于近 <b>{{ days }}</b> 天的运营数据</div>
      </div>
      <el-radio-group v-model="days" size="default">
        <el-radio-button :value="7">近 7 天</el-radio-button>
        <el-radio-button :value="30">近 30 天</el-radio-button>
        <el-radio-button :value="90">近 90 天</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 顶部 4 个数字 KPI -->
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-icon" style="background: rgba(200,164,140,0.15); color: #A4836B"><Icon name="circle-dollar-sign" :size="20" /></div>
        <div>
          <div class="kpi-lbl">营收</div>
          <div class="kpi-val">¥{{ (revenue.total / 100).toFixed(0) }}</div>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon" style="background: rgba(157,173,147,0.15); color: #5C7050"><Icon name="user-check" :size="20" /></div>
        <div>
          <div class="kpi-lbl">出席率</div>
          <div class="kpi-val">{{ (attendance.rate * 100).toFixed(1) }}%</div>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon" style="background: rgba(168,176,181,0.15); color: #6B7378"><Icon name="credit-card" :size="20" /></div>
        <div>
          <div class="kpi-lbl">在用卡</div>
          <div class="kpi-val">{{ liability.active_cards }}</div>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon" style="background: rgba(136,149,141,0.15); color: #6E7B73"><Icon name="wallet" :size="20" /></div>
        <div>
          <div class="kpi-lbl">未消费次数 + 储值</div>
          <div class="kpi-val">
            {{ liability.total_remaining_credits }} 次<span class="sm"> + ¥{{ (liability.total_remaining_balance/100).toFixed(0) }}</span>
          </div>
        </div>
      </div>
    </div>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="14">
        <div class="ys-card chart-card">
          <div class="ch-head">
            <span class="ch-title">每日营收</span>
            <span class="ch-tag">含线下收款</span>
          </div>
          <div ref="revRef" class="chart"></div>
        </div>
      </el-col>
      <el-col :span="10">
        <div class="ys-card chart-card">
          <div class="ch-head">
            <span class="ch-title">出席分布</span>
            <span class="ch-tag">{{ attendance.total }} 单预约</span>
          </div>
          <div ref="attRef" class="chart"></div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="14">
        <div class="ys-card chart-card">
          <div class="ch-head">
            <span class="ch-title">会员增长</span>
            <span class="ch-tag">柱：新增 / 线：累计</span>
          </div>
          <div ref="grRef" class="chart"></div>
        </div>
      </el-col>
      <el-col :span="10">
        <div class="ys-card chart-card">
          <div class="ch-head">
            <span class="ch-title">教练课时排行</span>
            <span class="ch-tag">按节数</span>
          </div>
          <div ref="chRef" class="chart"></div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.page-head { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 16px; }
.page-head h2 { margin: 0; font-size: 22px; font-weight: 500; letter-spacing: 1px; }
.sub { color: var(--ys-text-muted); font-size: 13px; margin-top: 4px; }
.sub b { color: var(--ys-primary-deep); font-weight: 500; }

.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}
.kpi-card {
  background: var(--ys-bg-card);
  border-radius: var(--ys-radius);
  padding: 16px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  border: 1px solid var(--ys-line);
}
.kpi-icon {
  width: 44px; height: 44px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  flex: none;
}
.kpi-lbl { font-size: 11px; color: var(--ys-text-muted); letter-spacing: 2px; }
.kpi-val {
  font-size: 22px;
  font-weight: 400;
  color: var(--ys-text);
  margin-top: 4px;
  font-variant-numeric: tabular-nums;
}
.kpi-val .sm { font-size: 13px; color: var(--ys-text-muted); }

.chart-card { padding: 16px; }
.ch-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px; }
.ch-title { font-size: 13px; font-weight: 500; letter-spacing: 1px; color: var(--ys-text); }
.ch-tag { font-size: 11px; color: var(--ys-text-muted); letter-spacing: 1px; }
.chart { height: 240px; }
</style>
