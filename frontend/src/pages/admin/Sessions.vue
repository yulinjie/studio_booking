<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api/client'
import dayjs from 'dayjs'
import { useSchedule } from '../../composables/useSchedule.js'
import SessionFormDialog from '../../components/admin/SessionFormDialog.vue'
import SessionBatchDialog from '../../components/admin/SessionBatchDialog.vue'
import SessionCloneDialog from '../../components/admin/SessionCloneDialog.vue'

const {
  sessions,
  courses,
  coaches,
  weekStart,
  weekEnd,
  days,
  sessionsByDay,
  courseName,
  coachName,
  colorByCourse,
  load,
  prevWeek,
  nextWeek,
  thisWeek,
} = useSchedule()

const view = ref('week')

// dialog 控制
const showOne = ref(false)
const showBatch = ref(false)
const showClone = ref(false)
const oneInitialDate = ref(null)
const oneInitialHour = ref(19)

// 时间槽：6:00 - 22:00, 每小时一格
const HOURS = Array.from({ length: 17 }, (_, i) => i + 6)

function sessionStyle(s) {
  const start = dayjs(s.start_at)
  const end = dayjs(s.end_at)
  const minFromTop = (start.hour() - 6) * 60 + start.minute()
  const dur = end.diff(start, 'minute')
  return { top: `${minFromTop}px`, height: `${Math.max(dur, 30) - 2}px` }
}

function openOne(date, hour) {
  oneInitialDate.value = date
  oneInitialHour.value = hour ?? 19
  showOne.value = true
}

function onCloned({ mode }) {
  if (mode === 'this_to_next') nextWeek()
  load()
}

async function cancel(s) {
  await ElMessageBox.confirm('取消整节课？已预约会员需要手工返还卡次', '确认', {
    type: 'warning',
  })
  await api.post(`/admin/sessions/${s.id}/cancel`)
  ElMessage.success('已取消')
  await load()
}

function exportCsv() {
  const params = new URLSearchParams({
    start: weekStart.value.toISOString(),
    end: weekEnd.value.toISOString(),
  })
  fetch(`/api/admin/export/bookings.csv?${params}`, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
  })
    .then((r) => r.blob())
    .then((blob) => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `bookings-${dayjs().format('YYYY-MM-DD')}.csv`
      a.click()
      URL.revokeObjectURL(url)
    })
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h2>排课</h2>
        <div class="sub">
          <span v-if="view === 'week'">
            {{ weekStart.format('M月D日') }} — {{ weekEnd.subtract(1, 'day').format('M月D日') }}
          </span>
          <span v-else>列表视图</span>
        </div>
      </div>
      <div class="actions">
        <el-radio-group v-model="view" size="default">
          <el-radio-button value="week">📅 周视图</el-radio-button>
          <el-radio-button value="list">☷ 列表</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <div class="toolbar">
      <template v-if="view === 'week'">
        <el-button-group>
          <el-button @click="prevWeek(); load()">‹ 上周</el-button>
          <el-button @click="thisWeek(); load()">本周</el-button>
          <el-button @click="nextWeek(); load()">下周 ›</el-button>
        </el-button-group>
      </template>
      <div style="flex: 1" />
      <el-button @click="exportCsv">导出预约 CSV</el-button>
      <el-button @click="showClone = true">📋 克隆排课</el-button>
      <el-button type="primary" @click="openOne(weekStart, 19)">+ 单节排课</el-button>
      <el-button type="success" @click="showBatch = true">+ 批量循环</el-button>
    </div>

    <!-- 周日历视图 -->
    <div v-if="view === 'week'" class="ys-card cal-card">
      <div class="cal-grid">
        <div class="cal-corner" />
        <div
          v-for="d in days"
          :key="d.format()"
          class="cal-day-head"
          :class="{ today: d.isSame(dayjs(), 'day') }"
        >
          <div class="day-wd">{{ ['日','一','二','三','四','五','六'][d.day()] }}</div>
          <div class="day-num">{{ d.format('D') }}</div>
        </div>

        <div class="cal-time-col">
          <div v-for="h in HOURS" :key="h" class="time-cell">
            {{ String(h).padStart(2, '0') }}:00
          </div>
        </div>

        <div
          v-for="d in days"
          :key="d.format() + '_col'"
          class="cal-day-col"
          @dblclick="openOne(d, 19)"
        >
          <div v-for="h in HOURS" :key="h" class="hour-cell" />
          <div
            v-for="s in sessionsByDay[d.format('YYYY-MM-DD')]"
            :key="s.id"
            class="cal-event"
            :style="{
              ...sessionStyle(s),
              background: colorByCourse(s.course_id).bg,
              borderLeftColor: colorByCourse(s.course_id).bd,
            }"
            :class="{ done: s.status === 'finished', cancelled: s.status === 'cancelled' }"
            @click.stop="$router.push(`/admin/check-in?sid=${s.id}`)"
          >
            <div class="ev-time">{{ dayjs(s.start_at).format('HH:mm') }}</div>
            <div class="ev-title">{{ courseName(s.course_id) }}</div>
            <div class="ev-meta">
              <span>{{ s.booked_count }}/{{ s.capacity }}</span>
              <span v-if="s.room">· {{ s.room }}</span>
            </div>
          </div>
        </div>
      </div>
      <div class="cal-tip">📌 双击空白处快速排课  ·  点击课节进入签到</div>
    </div>

    <!-- 列表视图 -->
    <div v-else class="ys-card" style="padding: 16px">
      <el-table :data="sessions" empty-text="该时段没有排课">
        <el-table-column label="时间" width="200">
          <template #default="{ row }">
            {{ dayjs(row.start_at).format('MM-DD ddd HH:mm') }} -
            {{ dayjs(row.end_at).format('HH:mm') }}
          </template>
        </el-table-column>
        <el-table-column label="课程" width="180">
          <template #default="{ row }">{{ courseName(row.course_id) }}</template>
        </el-table-column>
        <el-table-column label="教练" width="140">
          <template #default="{ row }">{{ coachName(row.coach_id) }}</template>
        </el-table-column>
        <el-table-column label="人数" width="100">
          <template #default="{ row }">
            <span :class="{ full: row.booked_count >= row.capacity }">
              {{ row.booked_count }} / {{ row.capacity }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="room" label="教室" width="100" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column label="操作">
          <template #default="{ row }">
            <router-link :to="`/admin/check-in?sid=${row.id}`">
              <el-button size="small" link type="primary">签到</el-button>
            </router-link>
            <el-button
              v-if="row.status === 'scheduled'"
              size="small"
              link
              type="danger"
              @click="cancel(row)"
            >
              取消
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <SessionFormDialog
      v-model="showOne"
      :courses="courses"
      :coaches="coaches"
      :initial-date="oneInitialDate"
      :initial-hour="oneInitialHour"
      @created="load"
    />
    <SessionBatchDialog
      v-model="showBatch"
      :courses="courses"
      :coaches="coaches"
      :initial-start-date="weekStart.toISOString().slice(0, 19)"
      @created="load"
    />
    <SessionCloneDialog
      v-model="showClone"
      :week-start="weekStart"
      :week-end="weekEnd"
      @cloned="onCloned"
    />
  </div>
</template>

<style scoped>
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 16px;
}
.page-head h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 500;
  letter-spacing: 1px;
}
.sub {
  color: var(--ys-text-muted);
  font-size: 13px;
  margin-top: 4px;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.cal-card {
  padding: 0;
  overflow: hidden;
}
.cal-grid {
  display: grid;
  grid-template-columns: 64px repeat(7, 1fr);
  position: relative;
}
.cal-corner {
  background: var(--ys-bg-soft);
  border-right: 1px solid var(--ys-line);
  border-bottom: 1px solid var(--ys-line);
}
.cal-day-head {
  text-align: center;
  padding: 12px 0;
  background: var(--ys-bg-soft);
  border-bottom: 1px solid var(--ys-line);
  border-right: 1px solid var(--ys-line);
}
.cal-day-head:last-child {
  border-right: 0;
}
.cal-day-head.today {
  background: var(--ys-primary-bg);
}
.day-wd {
  font-size: 11px;
  color: var(--ys-text-muted);
  letter-spacing: 2px;
}
.day-num {
  font-size: 18px;
  font-weight: 500;
  color: var(--ys-text);
  margin-top: 2px;
}
.cal-day-head.today .day-num {
  color: var(--ys-primary-deep);
}

.cal-time-col {
  border-right: 1px solid var(--ys-line);
}
.time-cell {
  height: 60px;
  font-size: 11px;
  color: var(--ys-text-muted);
  text-align: right;
  padding: 2px 8px 0 0;
  border-bottom: 1px dashed var(--ys-line);
  font-variant-numeric: tabular-nums;
}

.cal-day-col {
  position: relative;
  border-right: 1px solid var(--ys-line);
  cursor: crosshair;
}
.cal-day-col:last-child {
  border-right: 0;
}
.hour-cell {
  height: 60px;
  border-bottom: 1px dashed var(--ys-line);
}

.cal-event {
  position: absolute;
  left: 4px;
  right: 4px;
  border-left: 3px solid;
  border-radius: 4px;
  padding: 4px 6px;
  font-size: 11px;
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.15s, box-shadow 0.15s;
}
.cal-event:hover {
  transform: translateY(-1px);
  box-shadow: var(--ys-shadow);
  z-index: 2;
}
.cal-event.done {
  opacity: 0.55;
}
.cal-event.cancelled {
  opacity: 0.4;
  text-decoration: line-through;
}
.ev-time {
  font-size: 10px;
  color: var(--ys-text-muted);
  font-variant-numeric: tabular-nums;
}
.ev-title {
  font-size: 12px;
  font-weight: 500;
  color: var(--ys-text);
  margin-top: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ev-meta {
  font-size: 10px;
  color: var(--ys-text-muted);
  margin-top: 1px;
}

.cal-tip {
  padding: 10px;
  text-align: center;
  font-size: 11px;
  color: var(--ys-text-muted);
  background: var(--ys-bg-soft);
  letter-spacing: 1px;
  border-top: 1px solid var(--ys-line);
}

.full {
  color: var(--ys-danger);
}
</style>
