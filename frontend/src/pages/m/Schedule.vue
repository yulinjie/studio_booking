<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { showDialog, showSuccessToast, showFailToast, showToast } from 'vant'
import { useRouter } from 'vue-router'
import api from '../../api/client'
import dayjs from 'dayjs'
import StudioLogo from '../../components/StudioLogo.vue'
import EmptyState from '../../components/EmptyState.vue'
import ListSkeleton from '../../components/ListSkeleton.vue'
import Icon from '../../components/Icon.vue'
// eslint-disable-next-line no-unused-vars
import { colorFor, gradient } from '../../composables/categoryColors.js'

const router = useRouter()
const dayOffset = ref(0)
const sessions = ref([])
const courses = ref([])
const coaches = ref([])
const categories = ref([])
const myBookings = ref([])
const studio = ref({ name: '云舍', announcement: '' })
const loading = ref(false)
const refreshing = ref(false)
const firstLoaded = ref(false)

const days = computed(() => Array.from({ length: 14 }, (_, i) => {
  const d = dayjs().add(i, 'day')
  return {
    offset: i,
    date: d.format('D'),
    wd: i === 0 ? '今' : (i === 1 ? '明' : ['日','一','二','三','四','五','六'][d.day()]),
    month: d.format('M'),
  }
}))

async function load() {
  loading.value = true
  try {
    const day = dayjs().add(dayOffset.value, 'day')
    const [sess, c, co, cat, mb] = await Promise.all([
      api.get('/sessions', { params: { start: day.startOf('day').toISOString(), end: day.endOf('day').toISOString() } }),
      courses.value.length ? Promise.resolve(courses.value) : api.get('/courses'),
      coaches.value.length ? Promise.resolve(coaches.value) : api.get('/coaches'),
      categories.value.length ? Promise.resolve(categories.value) : api.get('/course-categories'),
      api.get('/me/bookings', { params: { upcoming: true } }),
    ])
    sessions.value = sess
    courses.value = c
    coaches.value = co
    categories.value = cat
    myBookings.value = mb
    if (!studio.value._loaded) {
      try { studio.value = { ...await api.get('/studio/config'), _loaded: true } } catch (e) { console.warn('[Schedule] studio config load failed:', e.message) }
    }
  } finally { loading.value = false; firstLoaded.value = true }
}

async function onRefresh() {
  refreshing.value = true
  try { await load() } finally { refreshing.value = false }
}

watch(dayOffset, load)
onMounted(load)

const findCourse = (id) => courses.value.find(c => c.id === id)
const courseName = (id) => findCourse(id)?.name || '课程'
const courseCover = (id) => findCourse(id)?.cover
const courseCredit = (id) => findCourse(id)?.credit_cost ?? 1
const coachTitle = (id) => coaches.value.find(c => c.id === id)?.title || ''
const courseDifficulty = (id) => findCourse(id)?.difficulty || 0
const categoryCode = (cid) => {
  const cat = categories.value.find(c => c.id === findCourse(cid)?.category_id)
  return cat?.code || 'default'
}
const categoryLabel = (cid) => {
  const cat = categories.value.find(c => c.id === findCourse(cid)?.category_id)
  return cat?.name || ''
}
const categoryGradient = (cid) => gradient(categoryCode(cid))
const myBooking = (sid) => myBookings.value.find(b => b.session_id === sid && ['booked','waitlist'].includes(b.status))

async function book(s) {
  const cName = courseName(s.course_id)
  const credit = courseCredit(s.course_id)
  try {
    await showDialog({
      title: '确认预约',
      message: `${cName}\n${dayjs(s.start_at).format('M月D日 HH:mm')}\n${s.booked_count >= s.capacity ? '满员，将进入候补' : `扣 ${credit} 次`}`,
      showCancelButton: true,
      confirmButtonText: '确认',
      confirmButtonColor: '#88958D',
    })
  } catch { return }
  try {
    const r = await api.post('/bookings', { session_id: s.id })
    showSuccessToast(r.message || '预约成功')
    await load()
  } catch (e) { showFailToast(e.message) }
}

async function cancel(s) {
  const b = myBooking(s.id)
  if (!b) return
  try { await showDialog({ title: '取消预约？', message: '取消后按规则可能不返还卡次', showCancelButton: true, confirmButtonColor: '#C8927E' }) } catch { return }
  try {
    const r = await api.post(`/bookings/${b.id}/cancel`)
    if (r.status === 'late_cancelled') showToast('超时取消，未返还卡次')
    else showSuccessToast('已取消')
    await load()
  } catch (e) { showFailToast(e.message) }
}

function isPast(s) { return dayjs(s.start_at).isBefore(dayjs()) }
function isFull(s) { return s.booked_count >= s.capacity }
function statusText(s) {
  const b = myBooking(s.id)
  if (b?.status === 'waitlist') return `候补#${b.waitlist_order}`
  if (b?.status === 'booked') return '已预约'
  if (isPast(s)) return '已开始'
  if (s.status !== 'scheduled') return ({finished:'已结束',cancelled:'已取消'})[s.status] || s.status
  if (isFull(s)) return '满员候补'
  return ''
}
</script>

<template>
  <div class="page">
    <header class="header">
      <div class="brand">
        <StudioLogo size="sm" :show-tag="false" />
        <span v-if="studio.name && studio.name !== '云舍'" class="studio-name">{{ studio.name }}</span>
      </div>
      <div v-if="studio.announcement" class="announce">📣 {{ studio.announcement }}</div>
    </header>

    <div class="day-strip">
      <div
v-for="d in days" :key="d.offset"
           class="day-pill"
           :class="{ active: dayOffset === d.offset }" @click="dayOffset = d.offset">
        <div class="wd">{{ d.wd }}</div>
        <div class="dt">{{ d.date }}</div>
      </div>
    </div>

    <ListSkeleton v-if="!firstLoaded" :count="3" />
    <van-pull-refresh v-else v-model="refreshing" @refresh="onRefresh">
    <div class="list">
      <EmptyState v-if="!sessions.length" illust="calendar" title="这天没有排课" sub="切换其他日期看看" />

      <div v-for="s in sessions" :key="s.id" class="card" :class="{ past: isPast(s), full: isFull(s) && !myBooking(s.id) }">
        <div v-if="courseCover(s.course_id)" class="cover" :style="{ backgroundImage: `url(${courseCover(s.course_id)})` }">
          <div class="cover-mask"></div>
          <span class="cat-badge cat-badge-img">{{ categoryLabel(s.course_id) }}</span>
          <span v-if="courseDifficulty(s.course_id)" class="diff-badge">
            <span v-for="i in 5" :key="i" :class="['s', i <= courseDifficulty(s.course_id) ? 'on' : '']">●</span>
          </span>
        </div>
        <div v-else class="cover cover-cat" :style="{ background: categoryGradient(s.course_id) }">
          <div class="cover-pattern">
            <Icon name="flower-2" :size="40" color="rgba(255,255,255,0.55)" :stroke="1.2" />
          </div>
          <span class="cat-badge">{{ categoryLabel(s.course_id) }}</span>
          <span v-if="courseDifficulty(s.course_id)" class="diff-badge">
            <span v-for="i in 5" :key="i" :class="['s', i <= courseDifficulty(s.course_id) ? 'on' : '']">●</span>
          </span>
        </div>

        <div class="card-body">
          <div class="time-block">
            <div class="t-start">{{ dayjs(s.start_at).format('HH:mm') }}</div>
            <div class="t-dur">{{ Math.round((dayjs(s.end_at).diff(dayjs(s.start_at))/60000)) }}'</div>
          </div>
          <div class="info">
            <div class="title">{{ courseName(s.course_id) }}</div>
            <div class="meta">
              <span v-if="s.coach_id" class="coach-link" @click.stop="$router.push(`/m/coach/${s.coach_id}`)">{{ coachTitle(s.coach_id) || '教练' }} ›</span>
              <span v-if="s.room">· {{ s.room }}</span>
            </div>
            <div class="cap">
              <div class="cap-bar"><div class="cap-fill" :style="{ width: `${(s.booked_count/s.capacity)*100}%` }"></div></div>
              <span class="cap-text">{{ s.booked_count }}/{{ s.capacity }}</span>
            </div>
          </div>
          <div class="action">
            <div v-if="statusText(s)" class="status-tag" :class="{ 'is-booked': !!myBooking(s.id), 'is-past': isPast(s) }">
              {{ statusText(s) }}
            </div>
            <van-button v-if="myBooking(s.id) && !isPast(s)" size="small" plain type="danger" round @click="cancel(s)">取消</van-button>
            <van-button v-else-if="!isPast(s) && s.status === 'scheduled'" size="small" type="primary" round @click="book(s)">
              {{ isFull(s) ? '候补' : '预约' }}
            </van-button>
          </div>
        </div>
      </div>
    </div>
    </van-pull-refresh>
  </div>
</template>

<style scoped>
.page { min-height: 100vh; }
.header {
  background: linear-gradient(180deg, #FFFFFF 0%, #F7F3EC 100%);
  padding: 14px 16px 12px;
  border-bottom: 1px solid var(--ys-line);
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.studio-name {
  font-size: 13px;
  color: var(--ys-text-muted);
  letter-spacing: 2px;
}
.announce {
  margin-top: 8px;
  font-size: 12px;
  color: var(--ys-text-soft);
  background: var(--ys-bg-soft);
  padding: 6px 10px;
  border-radius: 6px;
}

.day-strip {
  position: sticky;
  top: 0;
  z-index: 9;
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  overflow-x: auto;
  background: rgba(247, 243, 236, 0.92);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--ys-line);
}
.day-strip::-webkit-scrollbar { display: none; }
.day-pill {
  flex: none;
  min-width: 48px;
  text-align: center;
  padding: 8px 0;
  border-radius: 12px;
  background: var(--ys-bg-card);
  border: 1px solid var(--ys-line);
  cursor: pointer;
  transition: all 0.18s;
}
.day-pill .wd {
  font-size: 11px;
  color: var(--ys-text-muted);
  letter-spacing: 1px;
}
.day-pill .dt {
  font-size: 18px;
  font-weight: 500;
  color: var(--ys-text);
  margin-top: 2px;
}
.day-pill.active {
  background: var(--ys-primary);
  border-color: var(--ys-primary);
}
.day-pill.active .wd, .day-pill.active .dt { color: white; }

.list { padding: 16px; display: flex; flex-direction: column; gap: 12px; }

.card {
  background: var(--ys-bg-card);
  border-radius: var(--ys-radius-lg);
  border: 1px solid var(--ys-line);
  overflow: hidden;
  box-shadow: var(--ys-shadow-sm);
  transition: all 0.18s;
}
.card.past { opacity: 0.55; }
.card.full { background: linear-gradient(180deg, #FFFFFF, #F8F2EC); }

.cover {
  height: 100px;
  position: relative;
  background-size: cover;
  background-position: center;
  background-color: #DDE5DC;
}
.cover-mask {
  position: absolute; inset: 0;
  background: linear-gradient(180deg, transparent 50%, rgba(0,0,0,0.15) 100%);
}
.cover-cat .cover-pattern {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  background-image: radial-gradient(circle at 20% 30%, rgba(255,255,255,0.18) 0%, transparent 35%),
                    radial-gradient(circle at 80% 70%, rgba(255,255,255,0.12) 0%, transparent 30%);
}
.cat-badge {
  position: absolute;
  top: 8px; left: 10px;
  font-size: 10px;
  letter-spacing: 2px;
  background: rgba(255,255,255,0.5);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  color: var(--ys-text);
  padding: 2px 8px;
  border-radius: 8px;
}
.cat-badge-img {
  background: rgba(0,0,0,0.35);
  color: white;
}
.diff-badge {
  position: absolute;
  bottom: 8px; right: 10px;
  display: inline-flex;
  gap: 1px;
  background: rgba(255,255,255,0.5);
  backdrop-filter: blur(6px);
  padding: 2px 6px;
  border-radius: 6px;
}
.diff-badge .s { font-size: 6px; color: rgba(255,255,255,0.5); line-height: 1; }
.diff-badge .s.on { color: #C8A48C; }
.cover[style*="background-image"] .diff-badge { background: rgba(0,0,0,0.35); }
.cover[style*="background-image"] .diff-badge .s { color: rgba(255,255,255,0.4); }
.cover[style*="background-image"] .diff-badge .s.on { color: #FFE9C2; }

.card-body {
  padding: 14px 14px 14px 14px;
  display: grid;
  grid-template-columns: 64px 1fr auto;
  gap: 14px;
  align-items: center;
}
.time-block {
  text-align: center;
  border-right: 1px solid var(--ys-line);
  padding-right: 14px;
}
.t-start {
  font-size: 22px;
  font-weight: 500;
  color: var(--ys-text);
  letter-spacing: 0.5px;
}
.t-dur {
  font-size: 11px;
  color: var(--ys-text-muted);
  margin-top: 2px;
}

.info { min-width: 0; }
.title {
  font-size: 16px;
  font-weight: 500;
  color: var(--ys-text);
  letter-spacing: 0.5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meta {
  font-size: 12px;
  color: var(--ys-text-muted);
  margin-top: 2px;
}
.coach-link {
  color: var(--ys-primary-deep);
  cursor: pointer;
}
.coach-link:active { opacity: 0.6; }
.cap {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}
.cap-bar {
  flex: 1;
  height: 4px;
  background: var(--ys-bg-soft);
  border-radius: 2px;
  overflow: hidden;
}
.cap-fill {
  height: 100%;
  background: var(--ys-primary);
  transition: width 0.3s;
}
.cap-text {
  font-size: 11px;
  color: var(--ys-text-muted);
  font-variant-numeric: tabular-nums;
}

.action {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  min-width: 60px;
}
.status-tag {
  font-size: 11px;
  color: var(--ys-text-muted);
  padding: 2px 8px;
  background: var(--ys-bg-soft);
  border-radius: 10px;
}
.status-tag.is-booked { color: var(--ys-primary-deep); background: var(--ys-primary-bg); }
.status-tag.is-past { color: var(--ys-text-light); }

.empty {
  text-align: center;
  padding: 80px 20px;
  color: var(--ys-text-muted);
}
.empty-icon {
  font-size: 60px;
  color: var(--ys-text-light);
  font-weight: 100;
  line-height: 1;
}
.empty-text { font-size: 14px; margin-top: 16px; letter-spacing: 1px; }
.empty-sub { font-size: 12px; color: var(--ys-text-light); margin-top: 4px; }
.loading-pulse {
  width: 40px; height: 40px; margin: 0 auto;
  border-radius: 50%;
  background: var(--ys-primary-bg);
  animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { transform: scale(0.85); opacity: 0.6; }
  50% { transform: scale(1); opacity: 1; }
}
</style>
