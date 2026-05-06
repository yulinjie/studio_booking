<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/client'
import dayjs from 'dayjs'
import Icon from '../../components/Icon.vue'
import PracticeStats from '../../components/PracticeStats.vue'
import { useAuth } from '../../stores/auth'
import { gradient } from '../../composables/categoryColors.js'

const router = useRouter()
const auth = useAuth()
const studio = ref({ name: '云舍', announcement: '', logo: null })
const todaySessions = ref([])
const courses = ref([])
const coaches = ref([])
const categories = ref([])
const myCoupons = ref([])
const myCardsCount = ref(0)

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '晚安'
  if (h < 11) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

async function load() {
  try {
    studio.value = await api.get('/studio/config')
  } catch {}
  const start = dayjs().startOf('day').toISOString()
  const end = dayjs().endOf('day').toISOString()
  const [s, c, co, cat, cps, cards] = await Promise.all([
    api.get('/sessions', { params: { start, end } }),
    api.get('/courses'),
    api.get('/coaches'),
    api.get('/course-categories'),
    api.get('/me/coupons', { params: { status: 'unused' } }).catch(() => []),
    api.get('/me/cards').catch(() => []),
  ])
  todaySessions.value = s
  courses.value = c
  coaches.value = co
  categories.value = cat
  myCoupons.value = cps
  myCardsCount.value = cards.filter(c => c.status === 'active').length
}

const courseCategoryCode = (courseId) => {
  const c = courses.value.find(x => x.id === courseId)
  return categories.value.find(cat => cat.id === c?.category_id)?.code || 'default'
}

const findCourse = (id) => courses.value.find(c => c.id === id)
const findCoach = (id) => coaches.value.find(c => c.id === id)

function goSchedule() { router.push('/m/schedule') }
function goCourse(id) { router.push(`/m/course/${id}`) }
function goCoupons() { router.push('/m/my-coupons') }
function goCards() { router.push('/m/my-cards') }

onMounted(load)
</script>

<template>
  <div class="page">
    <!-- Hero -->
    <header class="hero">
      <div class="hero-bg">
        <div class="bb b1"></div><div class="bb b2"></div>
      </div>
      <div class="hero-content">
        <div class="hi">
          <div class="greet">{{ greeting }}，<b>{{ auth.user?.name }}</b></div>
          <div class="date">{{ dayjs().format('M 月 D 日 dddd') }}</div>
        </div>
        <img v-if="studio.logo" :src="studio.logo" class="logo-img" />
        <div v-else class="cloud-mark">
          <svg viewBox="0 0 40 28" width="32" height="22"><path d="M8 22 Q3 22 3 17 Q3 12 8 12 Q8 6 14 6 Q19 6 21 9 Q24 7 28 9 Q35 9 35 16 Q39 16 39 21 Q39 26 33 26 L8 26 Q3 26 8 22 Z" stroke="rgba(255,255,255,0.7)" stroke-width="1.4" fill="none"/></svg>
        </div>
      </div>
    </header>

    <!-- 公告条 -->
    <div v-if="studio.announcement" class="announce">
      <Icon name="megaphone" :size="14" />
      <span>{{ studio.announcement }}</span>
    </div>

    <!-- 练习统计 -->
    <div class="block">
      <PracticeStats />
    </div>

    <!-- 快捷入口 -->
    <div class="quick">
      <div class="q-item" @click="goCards">
        <div class="q-icon" style="background: linear-gradient(135deg, #DDE5DC, #B5C4A7)">
          <Icon name="wallet" :size="20" color="#6E7B73" />
        </div>
        <div class="q-text">
          <div class="q-num">{{ myCardsCount }}</div>
          <div class="q-lbl">在用卡</div>
        </div>
      </div>
      <div class="q-item" @click="goCoupons">
        <div class="q-icon" style="background: linear-gradient(135deg, #FAEEDE, #C8A48C)">
          <Icon name="ticket-percent" :size="20" color="#A4836B" />
        </div>
        <div class="q-text">
          <div class="q-num">{{ myCoupons.length }}</div>
          <div class="q-lbl">优惠券</div>
        </div>
      </div>
      <div class="q-item" @click="$router.push('/m/my-bookings')">
        <div class="q-icon" style="background: linear-gradient(135deg, #EDE0E1, #C8A8A8)">
          <Icon name="bookmark" :size="20" color="#9C7676" />
        </div>
        <div class="q-text">
          <div class="q-num">›</div>
          <div class="q-lbl">我的预约</div>
        </div>
      </div>
    </div>

    <!-- 今日课程 -->
    <div class="block">
      <div class="block-head">
        <h3>今日课程</h3>
        <span class="more" @click="goSchedule">本周课表 ›</span>
      </div>
      <div v-if="!todaySessions.length" class="empty-mini">
        <Icon name="moon" :size="32" color="#C5BFB6" :stroke="1.2" />
        <div>今天工作室休息，明天见</div>
      </div>
      <div v-else class="today-list">
        <div v-for="s in todaySessions" :key="s.id" class="t-card" @click="goCourse(s.course_id)">
          <div class="t-time">
            <div class="t-h">{{ dayjs(s.start_at).format('HH:mm') }}</div>
            <div class="t-min">{{ Math.round((dayjs(s.end_at).diff(dayjs(s.start_at))/60000)) }} 分钟</div>
          </div>
          <div class="t-info">
            <div class="t-name">{{ findCourse(s.course_id)?.name || '课程' }}</div>
            <div class="t-meta">
              <span v-if="findCoach(s.coach_id)?.title">
                <Icon name="user" :size="12" /> {{ findCoach(s.coach_id).title }}
              </span>
              <span v-if="s.room"><Icon name="map-pin" :size="12" /> {{ s.room }}</span>
            </div>
            <div class="t-cap">
              <Icon name="users" :size="12" />
              <span>{{ s.booked_count }}/{{ s.capacity }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 推荐课程 -->
    <div class="block" v-if="courses.length">
      <div class="block-head">
        <h3>课程推荐</h3>
      </div>
      <div class="course-strip">
        <div v-for="c in courses.slice(0, 6)" :key="c.id" class="c-card" @click="goCourse(c.id)">
          <div v-if="c.cover" class="c-cover" :style="{ backgroundImage: `url(${c.cover})` }"></div>
          <div v-else class="c-cover c-cover-default" :style="{ background: gradient(courseCategoryCode(c.id)) }">
            <Icon name="flower-2" :size="28" color="rgba(255,255,255,0.7)" />
          </div>
          <div class="c-body">
            <div class="c-name">{{ c.name }}</div>
            <div class="c-tags" v-if="c.tags">
              <span v-for="t in c.tags.split(/[,，、]\s*/).slice(0, 2)" :key="t" class="c-tag">{{ t }}</span>
            </div>
            <div class="c-stars" v-if="c.difficulty">
              <span v-for="i in 5" :key="i" :class="['star', i <= c.difficulty ? 'on' : '']">★</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 价值主张 -->
    <div class="philosophy">
      <div class="p-mark">「</div>
      <p>找到属于自己的呼吸节奏，<br/>在每一次练习里安放当下。</p>
      <div class="p-foot">— 云舍</div>
    </div>
  </div>
</template>

<style scoped>
.page { padding: 0 0 12px; }

/* Hero */
.hero {
  position: relative;
  background: linear-gradient(160deg, #DDE5DC 0%, #EFEAE0 100%);
  padding: 26px 20px 30px;
  overflow: hidden;
  border-radius: 0 0 24px 24px;
}
.hero-bg .bb { position: absolute; border-radius: 50%; filter: blur(40px); opacity: 0.5; }
.bb.b1 { width: 200px; height: 200px; background: #B5C4A7; top: -50px; right: -40px; }
.bb.b2 { width: 160px; height: 160px; background: #DCC5C6; bottom: -40px; left: -30px; }
.hero-content {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.greet { font-size: 17px; color: var(--ys-text); letter-spacing: 1px; }
.greet b { font-weight: 500; color: var(--ys-primary-deep); }
.date { font-size: 12px; color: var(--ys-text-muted); margin-top: 6px; letter-spacing: 1px; }
.cloud-mark, .logo-img {
  width: 50px; height: 50px;
  border-radius: 50%;
  background: rgba(255,255,255,0.5);
  backdrop-filter: blur(10px);
  border: 1.5px solid rgba(255,255,255,0.6);
  display: flex; align-items: center; justify-content: center;
}
.logo-img { object-fit: cover; }

/* Announcement */
.announce {
  margin: 14px 16px 0;
  padding: 9px 14px;
  background: linear-gradient(90deg, #FAEEDE 0%, #FFFFFF 80%);
  border: 1px solid #E8D4B6;
  border-radius: var(--ys-radius);
  font-size: 12px;
  color: #8C6940;
  display: flex; align-items: center; gap: 8px;
}

/* Block */
.block { padding: 16px 16px 4px; }
.block-head {
  display: flex; justify-content: space-between; align-items: baseline;
  margin-bottom: 10px;
}
.block h3 { margin: 0; font-size: 15px; font-weight: 500; letter-spacing: 1px; color: var(--ys-text); }
.more { font-size: 12px; color: var(--ys-primary-deep); letter-spacing: 1px; cursor: pointer; }

/* Quick entries */
.quick {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  padding: 16px 16px 0;
}
.q-item {
  background: var(--ys-bg-card);
  border-radius: var(--ys-radius);
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: var(--ys-shadow-sm);
  cursor: pointer;
  transition: transform 0.15s;
}
.q-item:active { transform: scale(0.98); }
.q-icon {
  width: 38px; height: 38px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  flex: none;
}
.q-text { min-width: 0; }
.q-num { font-size: 18px; font-weight: 500; color: var(--ys-text); line-height: 1; }
.q-lbl { font-size: 11px; color: var(--ys-text-muted); margin-top: 4px; letter-spacing: 1px; }

/* Today list */
.today-list { display: flex; flex-direction: column; gap: 8px; }
.t-card {
  background: var(--ys-bg-card);
  border-radius: var(--ys-radius);
  padding: 12px;
  display: grid;
  grid-template-columns: 70px 1fr;
  gap: 12px;
  align-items: center;
  box-shadow: var(--ys-shadow-sm);
  cursor: pointer;
  border: 1px solid var(--ys-line);
}
.t-time {
  text-align: center;
  border-right: 1px solid var(--ys-line);
  padding-right: 8px;
}
.t-h { font-size: 18px; font-weight: 500; color: var(--ys-text); font-variant-numeric: tabular-nums; }
.t-min { font-size: 10px; color: var(--ys-text-muted); margin-top: 2px; }
.t-info { min-width: 0; }
.t-name { font-size: 14px; font-weight: 500; color: var(--ys-text); }
.t-meta {
  display: flex;
  gap: 10px;
  margin-top: 3px;
  font-size: 11px;
  color: var(--ys-text-muted);
}
.t-meta span { display: inline-flex; align-items: center; gap: 3px; }
.t-cap { font-size: 11px; color: var(--ys-primary-deep); margin-top: 2px; display: inline-flex; align-items: center; gap: 3px; }

/* Empty mini */
.empty-mini {
  text-align: center;
  padding: 20px;
  color: var(--ys-text-muted);
  font-size: 12px;
}
.empty-mini > div { margin-top: 8px; letter-spacing: 1px; }

/* Course strip */
.course-strip {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 6px;
  margin: 0 -16px;
  padding-left: 16px;
  padding-right: 16px;
}
.course-strip::-webkit-scrollbar { display: none; }
.c-card {
  flex: none;
  width: 150px;
  background: var(--ys-bg-card);
  border-radius: var(--ys-radius);
  overflow: hidden;
  box-shadow: var(--ys-shadow-sm);
  border: 1px solid var(--ys-line);
  cursor: pointer;
}
.c-cover {
  height: 90px;
  background-size: cover;
  background-position: center;
}
.c-cover-default {
  display: flex; align-items: center; justify-content: center;
}
.c-body { padding: 8px 10px; }
.c-name { font-size: 13px; font-weight: 500; color: var(--ys-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.c-tags { margin-top: 4px; display: flex; gap: 4px; }
.c-tag {
  font-size: 10px;
  padding: 1px 6px;
  background: var(--ys-primary-bg);
  color: var(--ys-primary-deep);
  border-radius: 3px;
}
.c-stars { margin-top: 4px; font-size: 10px; }
.c-stars .star { color: #DDD7CC; }
.c-stars .star.on { color: #C8A48C; }

/* Philosophy */
.philosophy {
  text-align: center;
  margin: 28px 32px 8px;
  padding: 24px 16px;
  border-top: 1px solid var(--ys-line);
  position: relative;
}
.p-mark {
  position: absolute;
  top: 6px; left: 50%; transform: translateX(-50%);
  background: var(--ys-bg);
  color: var(--ys-text-light);
  font-size: 18px;
  padding: 0 12px;
}
.philosophy p {
  font-size: 14px;
  line-height: 1.9;
  color: var(--ys-text-soft);
  letter-spacing: 2px;
  margin: 8px 0;
}
.p-foot {
  font-size: 11px;
  color: var(--ys-text-light);
  letter-spacing: 4px;
  margin-top: 8px;
}
</style>
