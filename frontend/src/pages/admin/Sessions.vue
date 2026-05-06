<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api/client'
import dayjs from 'dayjs'
import { colorFor } from '../../composables/categoryColors.js'

const sessions = ref([])
const courses = ref([])
const coaches = ref([])
const categories = ref([])
const view = ref('week')   // 'week' | 'list'
const weekOffset = ref(0)

const showOne = ref(false)
const oneForm = ref({})
const showBatch = ref(false)
const batchForm = ref({})

const weekStart = computed(() => dayjs().startOf('week').add(1, 'day').add(weekOffset.value * 7, 'day'))
const weekEnd = computed(() => weekStart.value.add(7, 'day'))
const days = computed(() => Array.from({ length: 7 }, (_, i) => weekStart.value.add(i, 'day')))
// 时间槽：6:00 - 22:00, 1 小时一格
const HOURS = Array.from({ length: 17 }, (_, i) => i + 6)

async function load() {
  sessions.value = await api.get('/sessions', {
    params: { start: weekStart.value.toISOString(), end: weekEnd.value.toISOString() },
  })
  if (!courses.value.length) courses.value = await api.get('/admin/courses')
  if (!coaches.value.length) coaches.value = await api.get('/coaches')
  if (!categories.value.length) categories.value = await api.get('/admin/course-categories')
}

const courseName = (id) => courses.value.find(c => c.id === id)?.name || '-'
const coachName = (id) => coaches.value.find(c => c.id === id)?.title || ''

// 给每节课算"位置 + 高度"
function sessionStyle(s) {
  const start = dayjs(s.start_at)
  const end = dayjs(s.end_at)
  const minFromTop = (start.hour() - 6) * 60 + start.minute()
  const dur = end.diff(start, 'minute')
  return {
    top: `${minFromTop}px`,
    height: `${Math.max(dur, 30) - 2}px`,
  }
}

function colorByCourse(courseId) {
  const course = courses.value.find(c => c.id === courseId)
  const cat = categories.value.find(c => c.id === course?.category_id)
  const c = colorFor(cat?.code)
  return { bg: c.soft, bd: c.from }
}

function openOne(date, hour) {
  const start = dayjs(date).hour(hour || 19).minute(0).second(0).millisecond(0)
  oneForm.value = {
    course_id: courses.value[0]?.id,
    coach_id: null,
    start_at: start.toISOString().slice(0, 19),
    capacity: null, room: '',
  }
  showOne.value = true
}

async function createOne() {
  try {
    const body = { ...oneForm.value }
    if (!body.coach_id) delete body.coach_id
    if (!body.capacity) delete body.capacity
    await api.post('/admin/sessions', body)
    ElMessage.success('已排课')
    showOne.value = false
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

function openBatch() {
  batchForm.value = {
    course_id: courses.value[0]?.id,
    coach_id: null,
    weekdays: [0, 2, 4],
    time_of_day: '19:00',
    start_date: weekStart.value.toISOString().slice(0, 19),
    weeks: 4, capacity: null, room: '',
  }
  showBatch.value = true
}

async function createBatch() {
  try {
    const body = { ...batchForm.value }
    if (!body.coach_id) delete body.coach_id
    if (!body.capacity) delete body.capacity
    const data = await api.post('/admin/sessions/batch', body)
    ElMessage.success(`已批量创建 ${data.length} 节课`)
    showBatch.value = false
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

async function cancel(s) {
  await ElMessageBox.confirm(`取消整节课？已预约会员需要手工返还卡次`, '确认', { type: 'warning' })
  await api.post(`/admin/sessions/${s.id}/cancel`)
  ElMessage.success('已取消')
  await load()
}

function exportCsv() {
  const params = new URLSearchParams({ start: weekStart.value.toISOString(), end: weekEnd.value.toISOString() })
  fetch(`/api/admin/export/bookings.csv?${params}`, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
  }).then(r => r.blob()).then(blob => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `bookings-${dayjs().format('YYYY-MM-DD')}.csv`; a.click()
    URL.revokeObjectURL(url)
  })
}

const sessionsByDay = computed(() => {
  const out = {}
  for (const d of days.value) out[d.format('YYYY-MM-DD')] = []
  for (const s of sessions.value) {
    const k = dayjs(s.start_at).format('YYYY-MM-DD')
    if (k in out) out[k].push(s)
  }
  return out
})

onMounted(load)
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h2>排课</h2>
        <div class="sub">
          <span v-if="view === 'week'">{{ weekStart.format('M月D日') }} — {{ weekEnd.subtract(1, 'day').format('M月D日') }}</span>
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
          <el-button @click="weekOffset--; load()">‹ 上周</el-button>
          <el-button @click="weekOffset = 0; load()">本周</el-button>
          <el-button @click="weekOffset++; load()">下周 ›</el-button>
        </el-button-group>
      </template>
      <div style="flex: 1"></div>
      <el-button @click="exportCsv">导出预约 CSV</el-button>
      <el-button type="primary" @click="openOne(weekStart, 19)">+ 单节排课</el-button>
      <el-button type="success" @click="openBatch">+ 批量循环</el-button>
    </div>

    <!-- 周日历视图 -->
    <div v-if="view === 'week'" class="ys-card cal-card">
      <div class="cal-grid">
        <div class="cal-corner"></div>
        <div v-for="d in days" :key="d.format()" class="cal-day-head" :class="{ today: d.isSame(dayjs(), 'day') }">
          <div class="day-wd">{{ ['日','一','二','三','四','五','六'][d.day()] }}</div>
          <div class="day-num">{{ d.format('D') }}</div>
        </div>

        <div class="cal-time-col">
          <div v-for="h in HOURS" :key="h" class="time-cell">{{ String(h).padStart(2,'0') }}:00</div>
        </div>

        <div v-for="d in days" :key="d.format()+'_col'" class="cal-day-col" @dblclick="openOne(d, 19)">
          <div v-for="h in HOURS" :key="h" class="hour-cell"></div>
          <div v-for="s in sessionsByDay[d.format('YYYY-MM-DD')]" :key="s.id"
               class="cal-event"
               :style="{ ...sessionStyle(s), background: colorByCourse(s.course_id).bg, borderLeftColor: colorByCourse(s.course_id).bd }"
               :class="{ done: s.status === 'finished', cancelled: s.status === 'cancelled' }"
               @click.stop="$router.push(`/admin/check-in?sid=${s.id}`)">
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
            {{ dayjs(row.start_at).format('MM-DD ddd HH:mm') }} - {{ dayjs(row.end_at).format('HH:mm') }}
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
            <span :class="{ full: row.booked_count >= row.capacity }">{{ row.booked_count }} / {{ row.capacity }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="room" label="教室" width="100" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column label="操作">
          <template #default="{ row }">
            <router-link :to="`/admin/check-in?sid=${row.id}`">
              <el-button size="small" link type="primary">签到</el-button>
            </router-link>
            <el-button v-if="row.status === 'scheduled'" size="small" link type="danger" @click="cancel(row)">取消</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 单节排课 -->
    <el-dialog v-model="showOne" title="单节排课" width="500px">
      <el-form label-width="100px">
        <el-form-item label="课程">
          <el-select v-model="oneForm.course_id" style="width: 100%">
            <el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="教练">
          <el-select v-model="oneForm.coach_id" clearable style="width: 100%">
            <el-option v-for="c in coaches" :key="c.id" :label="c.title || ('教练'+c.id)" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker v-model="oneForm.start_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="容量"><el-input-number v-model="oneForm.capacity" :min="1" /></el-form-item>
        <el-form-item label="教室"><el-input v-model="oneForm.room" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showOne = false">取消</el-button>
        <el-button type="primary" @click="createOne">创建</el-button>
      </template>
    </el-dialog>

    <!-- 批量 -->
    <el-dialog v-model="showBatch" title="批量循环排课" width="550px">
      <el-form label-width="100px">
        <el-form-item label="课程">
          <el-select v-model="batchForm.course_id" style="width: 100%">
            <el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="教练">
          <el-select v-model="batchForm.coach_id" clearable style="width: 100%">
            <el-option v-for="c in coaches" :key="c.id" :label="c.title || ('教练'+c.id)" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="星期">
          <el-checkbox-group v-model="batchForm.weekdays">
            <el-checkbox :value="0">一</el-checkbox><el-checkbox :value="1">二</el-checkbox>
            <el-checkbox :value="2">三</el-checkbox><el-checkbox :value="3">四</el-checkbox>
            <el-checkbox :value="4">五</el-checkbox><el-checkbox :value="5">六</el-checkbox>
            <el-checkbox :value="6">日</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="时间"><el-input v-model="batchForm.time_of_day" placeholder="HH:MM 例如 19:00" /></el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="batchForm.start_date" type="date" value-format="YYYY-MM-DDT00:00:00" style="width: 100%" />
        </el-form-item>
        <el-form-item label="连续周数"><el-input-number v-model="batchForm.weeks" :min="1" :max="52" /></el-form-item>
        <el-form-item label="容量"><el-input-number v-model="batchForm.capacity" :min="1" /></el-form-item>
        <el-form-item label="教室"><el-input v-model="batchForm.room" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBatch = false">取消</el-button>
        <el-button type="primary" @click="createBatch">批量创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-head { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 16px; }
.page-head h2 { margin: 0; font-size: 22px; font-weight: 500; letter-spacing: 1px; }
.sub { color: var(--ys-text-muted); font-size: 13px; margin-top: 4px; }
.toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }

.cal-card { padding: 0; overflow: hidden; }
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
.cal-day-head:last-child { border-right: 0; }
.cal-day-head.today { background: var(--ys-primary-bg); }
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
.cal-day-head.today .day-num { color: var(--ys-primary-deep); }

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
.cal-day-col:last-child { border-right: 0; }
.hour-cell {
  height: 60px;
  border-bottom: 1px dashed var(--ys-line);
}

.cal-event {
  position: absolute;
  left: 4px; right: 4px;
  border-left: 3px solid;
  border-radius: 4px;
  padding: 4px 6px;
  font-size: 11px;
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.15s, box-shadow 0.15s;
}
.cal-event:hover { transform: translateY(-1px); box-shadow: var(--ys-shadow); z-index: 2; }
.cal-event.done { opacity: 0.55; }
.cal-event.cancelled { opacity: 0.4; text-decoration: line-through; }
.ev-time { font-size: 10px; color: var(--ys-text-muted); font-variant-numeric: tabular-nums; }
.ev-title {
  font-size: 12px;
  font-weight: 500;
  color: var(--ys-text);
  margin-top: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ev-meta { font-size: 10px; color: var(--ys-text-muted); margin-top: 1px; }

.cal-tip {
  padding: 10px;
  text-align: center;
  font-size: 11px;
  color: var(--ys-text-muted);
  background: var(--ys-bg-soft);
  letter-spacing: 1px;
  border-top: 1px solid var(--ys-line);
}

.full { color: var(--ys-danger); }
</style>
