<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showDialog, showSuccessToast, showFailToast } from 'vant'
import api from '../../api/client'
import dayjs from 'dayjs'
import Icon from '../../components/Icon.vue'

const route = useRoute()
const router = useRouter()
const courseId = Number(route.params.id)

const course = ref(null)
const category = ref(null)
const upcoming = ref([])
const coaches = ref([])
const evaluations = ref([])

async function load() {
  const courses = await api.get('/courses')
  course.value = courses.find(c => c.id === courseId)
  if (!course.value) return
  const cats = await api.get('/course-categories')
  category.value = cats.find(c => c.id === course.value.category_id)
  const sessions = await api.get('/sessions', {
    params: {
      start: dayjs().toISOString(),
      end: dayjs().add(14, 'day').toISOString(),
      course_id: courseId,
    },
  })
  upcoming.value = sessions
  coaches.value = await api.get('/coaches')
  try { evaluations.value = await api.get('/admin/evaluations', { params: { course_id: courseId } }) } catch (e) { console.warn('[CourseDetail] evaluations load failed:', e.message) }
}

const coachName = (id) => coaches.value.find(c => c.id === id)?.title || ''

const avgRating = computed(() => {
  if (!evaluations.value.length) return null
  const s = evaluations.value.reduce((a, e) => a + e.rating, 0)
  return (s / evaluations.value.length).toFixed(1)
})

async function book(s) {
  try {
    await showDialog({
      title: '确认预约',
      message: `${course.value.name}\n${dayjs(s.start_at).format('M月D日 HH:mm')}\n扣 ${course.value.credit_cost} 次`,
      showCancelButton: true, confirmButtonColor: '#88958D',
    })
  } catch { return }
  try {
    const r = await api.post('/bookings', { session_id: s.id })
    showSuccessToast(r.message || '预约成功')
    await load()
  } catch (e) { showFailToast(e.message) }
}

onMounted(load)
</script>

<template>
  <div v-if="course" class="page">
    <!-- Cover -->
    <div class="cover" :style="course.cover ? { backgroundImage: `url(${course.cover})` } : {}">
      <div v-if="!course.cover" class="cover-default">
        <Icon name="flower-2" :size="64" color="rgba(255,255,255,0.55)" />
      </div>
      <div class="cover-mask"></div>
      <div class="back" @click="router.back()">
        <Icon name="chevron-left" :size="22" color="white" />
      </div>
      <div v-if="category" class="cat-tag">{{ category.name }}</div>
    </div>

    <!-- Header -->
    <div class="head">
      <h2>{{ course.name }}</h2>
      <div class="row">
        <div class="stars">
          <span v-for="i in 5" :key="i" :class="['s', i <= course.difficulty ? 'on' : '']">★</span>
          <span class="diff-lbl">强度 {{ ['极轻','轻','中','较强','强'][course.difficulty - 1] }}</span>
        </div>
        <div v-if="avgRating" class="rate">
          <Icon name="star" :size="13" color="#C8A48C" />
          {{ avgRating }} <span>({{ evaluations.length }})</span>
        </div>
      </div>
      <div class="meta">
        <div class="m-item"><Icon name="clock" :size="14" /> {{ course.duration_minutes }} 分钟</div>
        <div class="m-item"><Icon name="users" :size="14" /> 容量 {{ course.capacity }}</div>
        <div class="m-item"><Icon name="circle-dollar-sign" :size="14" /> {{ course.credit_cost }} 次/节</div>
      </div>
      <div v-if="course.tags" class="tags">
        <span v-for="t in course.tags.split(/[,，、]\s*/)" :key="t" class="tag">{{ t }}</span>
      </div>
    </div>

    <!-- 介绍 -->
    <div v-if="course.description || course.suitable_for" class="section">
      <div class="s-title">课程介绍</div>
      <p v-if="course.description" class="desc">{{ course.description }}</p>
      <div v-if="course.suitable_for" class="suit">
        <Icon name="heart" :size="14" color="#C8A48C" />
        <span>适合：{{ course.suitable_for }}</span>
      </div>
    </div>

    <!-- 近期课节 -->
    <div class="section">
      <div class="s-title">近 14 天可约课节</div>
      <div v-if="!upcoming.length" class="empty">暂无可约课节</div>
      <div v-else class="sess-list">
        <div v-for="s in upcoming" :key="s.id" class="sess">
          <div class="sess-time">
            <div class="d">{{ dayjs(s.start_at).format('M-D') }}</div>
            <div class="w">{{ ['日','一','二','三','四','五','六'][dayjs(s.start_at).day()] }}</div>
            <div class="t">{{ dayjs(s.start_at).format('HH:mm') }}</div>
          </div>
          <div class="sess-info">
            <div class="sess-coach">{{ coachName(s.coach_id) || '— 教练 —' }}</div>
            <div v-if="s.room" class="sess-room"><Icon name="map-pin" :size="11" /> {{ s.room }}</div>
            <div class="sess-cap" :class="{ full: s.booked_count >= s.capacity }">
              {{ s.booked_count }}/{{ s.capacity }} 位
            </div>
          </div>
          <van-button
size="small" type="primary" round
                      :disabled="s.status !== 'scheduled' || dayjs(s.start_at).isBefore(dayjs())"
                      @click="book(s)">
            {{ s.booked_count >= s.capacity ? '候补' : '预约' }}
          </van-button>
        </div>
      </div>
    </div>

    <!-- 评价 -->
    <div v-if="evaluations.length" class="section">
      <div class="s-title">学员评价 ({{ evaluations.length }})</div>
      <div v-for="ev in evaluations.slice(0, 5)" :key="ev.id" class="ev">
        <div class="ev-stars">
          <span v-for="i in 5" :key="i" :class="['s', i <= ev.rating ? 'on' : '']">★</span>
        </div>
        <p v-if="ev.comment">{{ ev.comment }}</p>
        <div class="ev-foot">{{ dayjs(ev.created_at).format('M-D') }}</div>
      </div>
    </div>
  </div>

  <div v-else class="loading">
    <Icon name="loader-circle" :size="28" />
  </div>
</template>

<style scoped>
.page { padding-bottom: 24px; }

.cover {
  position: relative;
  height: 220px;
  background-size: cover;
  background-position: center;
  background-color: #DDE5DC;
  margin-bottom: -24px;
}
.cover-default {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #C8B498 0%, #DDE5DC 60%, #B5C4A7 100%);
  display: flex; align-items: center; justify-content: center;
}
.cover-mask {
  position: absolute; inset: 0;
  background: linear-gradient(180deg, rgba(0,0,0,0.15) 0%, transparent 30%, transparent 60%, rgba(247,243,236,0.95) 100%);
}
.back {
  position: absolute; top: 12px; left: 12px;
  width: 36px; height: 36px;
  border-radius: 50%;
  background: rgba(0,0,0,0.25);
  backdrop-filter: blur(8px);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
}
.cat-tag {
  position: absolute; top: 14px; right: 14px;
  background: rgba(255,255,255,0.85);
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 11px;
  letter-spacing: 2px;
  color: var(--ys-primary-deep);
}

.head {
  position: relative;
  padding: 16px 18px 8px;
  background: var(--ys-bg);
  border-radius: 16px 16px 0 0;
  z-index: 1;
}
.head h2 { margin: 0 0 8px; font-size: 22px; font-weight: 500; letter-spacing: 1px; }
.row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.stars { display: flex; align-items: center; gap: 6px; }
.s { color: #DDD7CC; font-size: 14px; }
.s.on { color: #C8A48C; }
.diff-lbl { font-size: 11px; color: var(--ys-text-muted); letter-spacing: 1px; margin-left: 4px; }
.rate { font-size: 13px; color: var(--ys-text-soft); display: flex; align-items: center; gap: 3px; }
.rate span { color: var(--ys-text-muted); font-size: 11px; }

.meta { display: flex; gap: 14px; margin-bottom: 10px; }
.m-item {
  font-size: 12px;
  color: var(--ys-text-muted);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.tags { display: flex; flex-wrap: wrap; gap: 5px; }
.tag {
  font-size: 11px;
  padding: 3px 9px;
  background: var(--ys-primary-bg);
  color: var(--ys-primary-deep);
  border-radius: 4px;
  letter-spacing: 0.5px;
}

.section { padding: 18px 18px 0; }
.s-title {
  font-size: 11px;
  color: var(--ys-text-muted);
  letter-spacing: 4px;
  margin-bottom: 10px;
}
.desc { font-size: 13px; line-height: 1.8; color: var(--ys-text-soft); margin: 0 0 10px; }
.suit {
  font-size: 12px;
  color: var(--ys-text-soft);
  background: rgba(200, 164, 140, 0.08);
  padding: 8px 12px;
  border-radius: var(--ys-radius-sm);
  display: flex; align-items: center; gap: 8px;
}

.sess-list { display: flex; flex-direction: column; gap: 8px; }
.sess {
  background: var(--ys-bg-card);
  border-radius: var(--ys-radius);
  padding: 12px;
  display: grid;
  grid-template-columns: 64px 1fr auto;
  gap: 12px;
  align-items: center;
  border: 1px solid var(--ys-line);
}
.sess-time { text-align: center; border-right: 1px solid var(--ys-line); padding-right: 12px; }
.sess-time .d { font-size: 14px; color: var(--ys-text); font-weight: 500; }
.sess-time .w { font-size: 11px; color: var(--ys-text-muted); margin: 2px 0; }
.sess-time .t { font-size: 13px; color: var(--ys-primary-deep); font-variant-numeric: tabular-nums; font-weight: 500; }
.sess-coach { font-size: 13px; color: var(--ys-text); }
.sess-room { font-size: 11px; color: var(--ys-text-muted); margin-top: 2px; display: inline-flex; align-items: center; gap: 3px; }
.sess-cap { font-size: 11px; color: var(--ys-success); margin-top: 2px; }
.sess-cap.full { color: var(--ys-danger); }

.ev {
  background: var(--ys-bg-card);
  border-radius: var(--ys-radius-sm);
  padding: 12px;
  margin-bottom: 8px;
}
.ev-stars { font-size: 13px; }
.ev p { font-size: 13px; color: var(--ys-text-soft); line-height: 1.6; margin: 6px 0 4px; }
.ev-foot { font-size: 11px; color: var(--ys-text-muted); }

.empty { text-align: center; color: var(--ys-text-muted); padding: 30px; font-size: 13px; }
.loading {
  min-height: 60vh;
  display: flex; align-items: center; justify-content: center;
  color: var(--ys-text-muted);
}
.loading svg { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
