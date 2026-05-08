<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import api from '../../api/client'

const month = ref(dayjs().format('YYYY-MM'))
const data = ref({ month: '', total_payroll: 0, coach_count: 0, coaches: [] })
const loading = ref(false)
const expanded = ref(null)
const detailMap = ref({})

async function load() {
  loading.value = true
  try {
    data.value = await api.get('/admin/payroll', { params: { month: month.value } })
  } catch (e) { ElMessage.error(e.message) } finally { loading.value = false }
}

async function toggleDetail(coach) {
  if (expanded.value === coach.coach_id) {
    expanded.value = null
    return
  }
  expanded.value = coach.coach_id
  if (!detailMap.value[coach.coach_id]) {
    detailMap.value[coach.coach_id] = await api.get(`/admin/payroll/${coach.coach_id}/sessions`, { params: { month: month.value } })
  }
}

const monthName = computed(() => dayjs(month.value + '-01').format('YYYY 年 M 月'))
const fen2yuan = (n) => (n / 100).toFixed(2)

function exportCsv() {
  const rows = [
    ['教练', '头衔', '底薪(元)', '节数', '签到人次', '课时费(元)', '人头补贴(元)', '提成(元)', '合计(元)'].join(','),
    ...data.value.coaches.map(c => [
      c.name, c.title || '', fen2yuan(c.base_salary), c.sessions_count, c.total_attendees,
      fen2yuan(c.sessions_pay), fen2yuan(c.attendee_pay), fen2yuan(c.commission_pay), fen2yuan(c.total),
    ].join(',')),
  ]
  const blob = new Blob(['﻿' + rows.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `payroll-${month.value}.csv`; a.click()
  URL.revokeObjectURL(url)
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h2>课时工资</h2>
        <div class="sub">{{ monthName }} · 共 {{ data.coach_count }} 位教练 · 总支出 ¥{{ fen2yuan(data.total_payroll) }}</div>
      </div>
      <div class="actions">
        <el-date-picker v-model="month" type="month" value-format="YYYY-MM" :clearable="false" @change="load" />
        <el-button @click="exportCsv">导出 CSV</el-button>
      </div>
    </div>

    <el-card v-loading="loading">
      <template #header>
        <div class="card-head">
          <span><b>本月工资条</b></span>
          <span class="card-tag">点开任一行可看每节课明细</span>
        </div>
      </template>

      <div v-if="!data.coaches.length" class="empty">
        <div class="empty-icon">○</div>
        <div class="empty-text">{{ monthName }} 没有结算工资</div>
        <div class="empty-sub">需要有 status=finished 的排课，且教练已配置薪酬</div>
      </div>

      <div v-else class="payroll-table">
        <table>
          <thead>
            <tr>
              <th class="col-name">教练</th>
              <th>底薪</th>
              <th>节数</th>
              <th>签到人次</th>
              <th>课时费</th>
              <th>人头补贴</th>
              <th>提成</th>
              <th class="col-total">合计</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <template v-for="c in data.coaches" :key="c.coach_id">
              <tr class="row" :class="{ active: expanded === c.coach_id }" @click="toggleDetail(c)">
                <td class="col-name">
                  <div class="coach-name">{{ c.name }}</div>
                  <div class="coach-title">{{ c.title || '—' }}</div>
                </td>
                <td>¥{{ fen2yuan(c.base_salary) }}</td>
                <td>{{ c.sessions_count }}</td>
                <td>{{ c.total_attendees }}</td>
                <td>¥{{ fen2yuan(c.sessions_pay) }}</td>
                <td>¥{{ fen2yuan(c.attendee_pay) }}</td>
                <td>¥{{ fen2yuan(c.commission_pay) }}</td>
                <td class="col-total">¥{{ fen2yuan(c.total) }}</td>
                <td class="col-arrow">{{ expanded === c.coach_id ? '▾' : '▸' }}</td>
              </tr>
              <tr v-if="expanded === c.coach_id" class="detail-row">
                <td colspan="9">
                  <div class="detail-wrap">
                    <div class="rates-line">
                      <span>📋 当前规则：</span>
                      <span>课时费 ¥{{ fen2yuan(c.rates.pay_per_session) }} / 节</span>
                      <span>人头补贴 ¥{{ fen2yuan(c.rates.pay_per_attendee) }} / 人</span>
                      <span>提成 {{ (c.rates.commission_bps / 100).toFixed(2) }}%</span>
                    </div>

                    <table v-if="detailMap[c.coach_id]?.length" class="detail-table">
                      <thead>
                        <tr>
                          <th>时间</th>
                          <th>课程</th>
                          <th>容量</th>
                          <th>签到</th>
                          <th>课时费</th>
                          <th>人头</th>
                          <th>提成</th>
                          <th>小计</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="s in detailMap[c.coach_id]" :key="s.session_id">
                          <td>{{ dayjs(s.start_at).format('M-D HH:mm') }}</td>
                          <td>{{ s.course_name }}</td>
                          <td>{{ s.capacity }}</td>
                          <td>{{ s.attendees }}</td>
                          <td>¥{{ fen2yuan(s.pay_per_session) }}</td>
                          <td>¥{{ fen2yuan(s.attendee_pay) }}</td>
                          <td>¥{{ fen2yuan(s.commission_pay) }}</td>
                          <td><b>¥{{ fen2yuan(s.subtotal) }}</b></td>
                        </tr>
                      </tbody>
                    </table>
                    <div v-else class="loading-detail">加载中...</div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </el-card>

    <el-alert type="info" show-icon :closable="false" style="margin-top: 16px">
      工资公式：底薪 + Σ(每节课课时费 + 签到人数 × 人头补贴 + 签到人数 × 课程价 × 提成%)。
      只统计已结算（status=finished）的排课。要修改某教练薪酬规则，去「教练」页面编辑。
    </el-alert>
  </div>
</template>

<style scoped>
.page-head { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 16px; }
.page-head h2 { margin: 0; font-size: 22px; font-weight: 500; letter-spacing: 1px; }
.sub { color: var(--ys-text-muted); font-size: 13px; margin-top: 4px; }
.actions { display: flex; gap: 8px; align-items: center; }

.card-head { display: flex; justify-content: space-between; align-items: baseline; }
.card-tag { font-size: 11px; color: var(--ys-text-muted); letter-spacing: 1px; }

.empty { text-align: center; padding: 60px 20px; color: var(--ys-text-muted); }
.empty-icon { font-size: 48px; color: var(--ys-text-light); }
.empty-text { font-size: 14px; margin-top: 12px; letter-spacing: 1px; }
.empty-sub { font-size: 12px; color: var(--ys-text-light); margin-top: 4px; }

.payroll-table { overflow-x: auto; }
.payroll-table table { width: 100%; border-collapse: collapse; font-size: 13px; }
.payroll-table th {
  background: var(--ys-bg-soft);
  color: var(--ys-text-soft);
  font-weight: 500;
  padding: 10px 12px;
  text-align: left;
  font-size: 12px;
  letter-spacing: 1px;
}
.payroll-table td { padding: 12px; border-bottom: 1px solid var(--ys-line); font-variant-numeric: tabular-nums; }
.col-name { width: 200px; }
.col-total { font-weight: 500; color: var(--ys-primary-deep); }
.col-arrow { width: 30px; color: var(--ys-text-light); text-align: center; }

.row { cursor: pointer; transition: background 0.15s; }
.row:hover { background: var(--ys-bg-soft); }
.row.active { background: var(--ys-primary-bg); }
.coach-name { font-weight: 500; color: var(--ys-text); }
.coach-title { font-size: 11px; color: var(--ys-text-muted); margin-top: 2px; }

.detail-row td { background: var(--ys-bg); padding: 0 !important; }
.detail-wrap { padding: 14px 16px 18px; }
.rates-line { font-size: 12px; color: var(--ys-text-muted); margin-bottom: 10px; display: flex; gap: 16px; flex-wrap: wrap; }
.detail-table { width: 100%; background: var(--ys-bg-card); border-radius: var(--ys-radius-sm); overflow: hidden; }
.detail-table th { background: transparent; font-size: 11px; padding: 8px 10px; }
.detail-table td { padding: 8px 10px; font-size: 12px; border-bottom: 1px solid var(--ys-line); }
.loading-detail { text-align: center; padding: 20px; color: var(--ys-text-muted); }
</style>
