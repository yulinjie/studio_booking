<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api/client'
import dayjs from 'dayjs'

const route = useRoute()
const sessions = ref([])
const courses = ref([])
const selectedSid = ref(Number(route.query.sid) || null)
const bookings = ref([])
const members = ref([])
const date = ref(dayjs().format('YYYY-MM-DD'))

async function loadSessions() {
  const start = dayjs(date.value).startOf('day').toISOString()
  const end = dayjs(date.value).endOf('day').toISOString()
  sessions.value = await api.get('/sessions', { params: { start, end } })
  if (!courses.value.length) courses.value = await api.get('/admin/courses')
  if (selectedSid.value && !sessions.value.find(s => s.id === selectedSid.value)) {
    selectedSid.value = sessions.value[0]?.id || null
  } else if (!selectedSid.value && sessions.value.length) {
    selectedSid.value = sessions.value[0].id
  }
}

async function loadBookings() {
  if (!selectedSid.value) { bookings.value = []; return }
  bookings.value = await api.get(`/admin/sessions/${selectedSid.value}/bookings`)
  // 拉每个会员的名字
  const ids = [...new Set(bookings.value.map(b => b.member_id))]
  if (ids.length) {
    const all = await api.get('/admin/members', { params: { size: 200 } })
    members.value = all.items.filter(m => ids.includes(m.id))
  }
}

watch(selectedSid, loadBookings)
watch(date, loadSessions)

const memberName = (id) => members.value.find(m => m.id === id)?.name || `#${id}`
const memberPhone = (id) => members.value.find(m => m.id === id)?.phone || ''
const currentSession = computed(() => sessions.value.find(s => s.id === selectedSid.value))
const courseName = (id) => courses.value.find(c => c.id === id)?.name || '-'

async function checkIn(b) {
  await api.post('/admin/check-in', { booking_id: b.id })
  ElMessage.success('已签到'); await loadBookings()
}

const showScan = ref(false)
const scanInput = ref('')
let scanInputEl = null

async function openScan() {
  showScan.value = true
  scanInput.value = ''
  await new Promise(r => setTimeout(r, 100))
  scanInputEl?.focus()
}

async function processScan() {
  const t = scanInput.value.trim()
  if (!t) return
  scanInput.value = ''
  try {
    const r = await api.post('/admin/check-in/scan', { token: t })
    ElMessage.success(`签到成功：${memberName(r.member_id)}`)
    await loadBookings()
    scanInputEl?.focus()    // 连续扫码
  } catch (e) {
    ElMessage.error(e.message)
    scanInputEl?.focus()
  }
}

async function markAllNoShow() {
  await ElMessageBox.confirm(`将本节课所有未签到的标为爽约？`, '确认', { type: 'warning' })
  const r = await api.post(`/admin/sessions/${selectedSid.value}/no-show`)
  ElMessage.success(`已标记 ${r.marked} 人爽约`); await loadBookings()
}

async function adminCancel(b) {
  await ElMessageBox.confirm(`代 ${memberName(b.member_id)} 取消预约？将全额返还卡次`, '确认', { type: 'warning' })
  await api.post(`/bookings/${b.id}/cancel`)
  ElMessage.success('已取消'); await loadBookings()
}

onMounted(async () => {
  await loadSessions()
  if (selectedSid.value) await loadBookings()
})
</script>

<template>
  <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 12px">
    <h2 style="margin: 0">今日签到</h2>
    <el-button type="primary" @click="openScan">📷 扫码签到</el-button>
  </div>
  <el-card style="margin-bottom: 16px">
    <div style="display: flex; gap: 16px; align-items: center; flex-wrap: wrap">
      <el-date-picker v-model="date" type="date" value-format="YYYY-MM-DD" />
      <el-radio-group v-model="selectedSid">
        <el-radio-button v-for="s in sessions" :key="s.id" :value="s.id">
          {{ dayjs(s.start_at).format('HH:mm') }} {{ courseName(s.course_id) }}
          <span style="opacity: .7">({{ s.booked_count }}/{{ s.capacity }})</span>
        </el-radio-button>
      </el-radio-group>
      <span v-if="!sessions.length" style="color: #888">该日期没有排课</span>
    </div>
  </el-card>

  <el-dialog v-model="showScan" title="扫描会员二维码" width="450px" @close="showScan = false">
    <el-alert type="info" show-icon :closable="false" style="margin-bottom: 14px">
      使用扫码枪/手机扫码：扫到的内容会自动填入下方输入框，回车即签到。<br>
      也支持手动粘贴二维码内容（YS-CHECKIN: 开头的字符串）。
    </el-alert>
    <el-input
      :ref="(el) => scanInputEl = el?.input"
      v-model="scanInput"
      placeholder="扫码或粘贴..."
      size="large"
      @keyup.enter="processScan"
      autofocus
    />
    <div style="margin-top: 8px; font-size: 12px; color: #888">
      💡 连续扫码：签到成功后自动清空、聚焦，可继续扫下一位
    </div>
    <template #footer>
      <el-button @click="showScan = false">关闭</el-button>
      <el-button type="primary" @click="processScan">提交</el-button>
    </template>
  </el-dialog>

  <el-card v-if="currentSession">
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <b>{{ courseName(currentSession.course_id) }} · {{ dayjs(currentSession.start_at).format('MM-DD HH:mm') }}</b>
        <el-button type="warning" size="small" @click="markAllNoShow">课后批量爽约</el-button>
      </div>
    </template>
    <el-table :data="bookings" empty-text="本节没有人预约">
      <el-table-column label="姓名">
        <template #default="{ row }">{{ memberName(row.member_id) }}</template>
      </el-table-column>
      <el-table-column label="手机号" width="140">
        <template #default="{ row }">{{ memberPhone(row.member_id) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'attended'" type="success" size="small">已签到</el-tag>
          <el-tag v-else-if="row.status === 'booked'" size="small">待签到</el-tag>
          <el-tag v-else-if="row.status === 'waitlist'" type="warning" size="small">候补#{{ row.waitlist_order }}</el-tag>
          <el-tag v-else-if="row.status === 'no_show'" type="danger" size="small">爽约</el-tag>
          <el-tag v-else type="info" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="预约时间" width="160">
        <template #default="{ row }">{{ dayjs(row.booked_at).format('MM-DD HH:mm') }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button v-if="row.status === 'booked'" type="primary" size="small" @click="checkIn(row)">签到</el-button>
          <el-button v-if="['booked','waitlist'].includes(row.status)" size="small" link type="danger" @click="adminCancel(row)">代取消</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>
