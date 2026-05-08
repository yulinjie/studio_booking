<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showSuccessToast, showFailToast, showDialog } from 'vant'
import api from '../../api/client'
import dayjs from 'dayjs'
import Icon from '../../components/Icon.vue'
import EmptyState from '../../components/EmptyState.vue'
import { safeSrc } from '../../composables/security.js'

const route = useRoute()
const router = useRouter()
const profile = ref(null)
const loading = ref(true)

async function load() {
  try {
    profile.value = await api.get(`/coaches/${route.params.id}/profile`)
  } catch (e) { showFailToast(e.message) } finally { loading.value = false }
}

const initial = computed(() => profile.value?.name?.[0] || '?')
const specialtyTags = computed(() =>
  profile.value?.specialties ? profile.value.specialties.split(/[,，、]\s*/).filter(Boolean) : []
)
const ratingDisplay = computed(() => {
  if (!profile.value?.avg_rating) return null
  return profile.value.avg_rating.toFixed(1)
})

const groupedByDay = computed(() => {
  if (!profile.value?.upcoming_sessions) return []
  const groups = {}
  for (const s of profile.value.upcoming_sessions) {
    const k = dayjs(s.start_at).format('YYYY-MM-DD')
    if (!groups[k]) groups[k] = []
    groups[k].push(s)
  }
  return Object.entries(groups).map(([date, sessions]) => ({ date, sessions }))
})

async function book(s) {
  try {
    await showDialog({
      title: '确认预约',
      message: `${s.course_name}\n${dayjs(s.start_at).format('M月D日 HH:mm')}\n教练：${profile.value.name}`,
      showCancelButton: true,
      confirmButtonColor: '#88958D',
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
  <div class="page">
    <header class="topbar">
      <div class="back" @click="router.back()"><Icon name="chevron-left" :size="20" /></div>
      <div class="title-text">教练详情</div>
      <div class="back-spacer"></div>
    </header>

    <div v-if="loading" class="loading">加载中...</div>

    <template v-else-if="profile">
      <!-- Hero -->
      <section class="hero">
        <div class="hero-bg">
          <div class="bb b1"></div>
          <div class="bb b2"></div>
        </div>
        <div class="profile-block">
          <div class="avatar-wrap">
            <img v-if="safeSrc(profile.avatar)" :src="safeSrc(profile.avatar)" class="avatar" />
            <div v-else class="avatar-fallback">{{ initial }}</div>
          </div>
          <div class="name">{{ profile.name }}</div>
          <div class="title">{{ profile.title || '— 教练 —' }}</div>

          <div class="rating-row">
            <div v-if="ratingDisplay" class="rating-pill">
              <Icon name="star" :size="13" /> {{ ratingDisplay }}
              <span class="rc">· {{ profile.rating_count }} 评</span>
            </div>
            <div v-else class="rating-pill rating-empty">
              <Icon name="star" :size="13" /> 暂无评分
            </div>
            <div class="stat-pill">
              带课 {{ profile.total_sessions_taught }} 节
            </div>
          </div>
        </div>
      </section>

      <!-- 擅长 -->
      <section v-if="specialtyTags.length" class="section">
        <div class="s-title">擅长</div>
        <div class="s-tags">
          <span v-for="t in specialtyTags" :key="t" class="s-tag">{{ t }}</span>
        </div>
      </section>

      <!-- 简介 -->
      <section v-if="profile.bio" class="section">
        <div class="s-title">关于教练</div>
        <p class="bio">{{ profile.bio }}</p>
      </section>

      <!-- 未来排课 -->
      <section class="section">
        <div class="s-title">最近 14 天排课</div>
        <EmptyState v-if="!profile.upcoming_sessions.length" illust="calendar" title="近期暂无排课" sub="过几天再来看看" />
        <div v-for="g in groupedByDay" :key="g.date" class="day-group">
          <div class="day-label">{{ dayjs(g.date).format('M月D日 dddd') }}</div>
          <div v-for="s in g.sessions" :key="s.id" class="sess-row">
            <div class="sess-time">{{ dayjs(s.start_at).format('HH:mm') }}</div>
            <div class="sess-mid">
              <div class="sess-course">{{ s.course_name }}</div>
              <div class="sess-meta">
                <span v-if="s.room"><Icon name="map-pin" :size="11" /> {{ s.room }}</span>
                <span><Icon name="users" :size="11" /> {{ s.booked_count }}/{{ s.capacity }}</span>
              </div>
            </div>
            <van-button v-if="s.booked_count < s.capacity" size="small" type="primary" round @click="book(s)">预约</van-button>
            <span v-else class="full-tag">满员</span>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.page { padding-bottom: 24px; }
.loading { padding: 80px 0; text-align: center; color: var(--ys-text-muted); }

.topbar {
  position: sticky;
  top: 0;
  z-index: 9;
  display: grid;
  grid-template-columns: 40px 1fr 40px;
  align-items: center;
  background: rgba(247, 243, 236, 0.92);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  padding: 12px 14px;
  border-bottom: 1px solid var(--ys-line);
}
.back { color: var(--ys-text); cursor: pointer; }
.title-text { text-align: center; font-size: 15px; letter-spacing: 1px; color: var(--ys-text); }

.hero {
  position: relative;
  padding: 40px 20px 28px;
  background: linear-gradient(160deg, #DDE5DC 0%, #EFEAE0 100%);
  overflow: hidden;
}
.hero-bg .bb {
  position: absolute;
  border-radius: 50%;
  filter: blur(40px);
  opacity: 0.5;
}
.bb.b1 { width: 200px; height: 200px; background: #B5C4A7; top: -60px; right: -50px; }
.bb.b2 { width: 160px; height: 160px; background: #C8A48C; bottom: -40px; left: -30px; }
.profile-block { position: relative; text-align: center; }

.avatar-wrap { display: inline-block; position: relative; }
.avatar, .avatar-fallback {
  width: 96px; height: 96px;
  border-radius: 50%;
  object-fit: cover;
  border: 3px solid rgba(255, 255, 255, 0.7);
  box-shadow: var(--ys-shadow);
}
.avatar-fallback {
  background: linear-gradient(135deg, var(--ys-primary-light), var(--ys-accent));
  color: white;
  line-height: 90px;
  font-size: 36px;
  font-weight: 300;
}

.name { font-size: 22px; letter-spacing: 2px; color: var(--ys-text); margin-top: 14px; font-weight: 400; }
.title { font-size: 13px; color: var(--ys-primary-deep); letter-spacing: 1.5px; margin-top: 4px; }

.rating-row { display: flex; justify-content: center; gap: 8px; margin-top: 14px; }
.rating-pill, .stat-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.7);
  font-size: 12px;
  color: var(--ys-text);
  letter-spacing: 0.5px;
}
.rating-pill { color: var(--ys-accent-deep); }
.rating-pill.rating-empty { color: var(--ys-text-muted); }
.rating-pill .rc { color: var(--ys-text-muted); margin-left: 2px; font-size: 11px; }

.section { padding: 18px 16px 0; }
.s-title { font-size: 11px; color: var(--ys-text-muted); letter-spacing: 4px; margin-bottom: 10px; padding-left: 4px; }
.s-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.s-tag {
  font-size: 12px;
  padding: 4px 12px;
  background: var(--ys-primary-bg);
  color: var(--ys-primary-deep);
  border-radius: 12px;
  letter-spacing: 0.5px;
}
.bio {
  margin: 0;
  font-size: 13px;
  line-height: 1.8;
  color: var(--ys-text-soft);
  background: var(--ys-bg-card);
  padding: 14px;
  border-radius: var(--ys-radius);
  letter-spacing: 0.3px;
}

.day-group { margin-bottom: 12px; }
.day-label { font-size: 12px; color: var(--ys-text-muted); margin-bottom: 6px; padding-left: 4px; letter-spacing: 0.5px; }
.sess-row {
  display: grid;
  grid-template-columns: 60px 1fr auto;
  align-items: center;
  gap: 12px;
  background: var(--ys-bg-card);
  border-radius: var(--ys-radius);
  padding: 12px 14px;
  margin-bottom: 6px;
  box-shadow: var(--ys-shadow-sm);
}
.sess-time { font-size: 18px; font-weight: 500; color: var(--ys-text); font-variant-numeric: tabular-nums; }
.sess-course { font-size: 14px; color: var(--ys-text); font-weight: 500; }
.sess-meta { font-size: 11px; color: var(--ys-text-muted); margin-top: 2px; display: flex; gap: 10px; align-items: center; }
.sess-meta span { display: flex; align-items: center; gap: 3px; }
.full-tag { font-size: 11px; color: var(--ys-text-muted); padding: 4px 10px; background: var(--ys-bg-soft); border-radius: 10px; }
</style>
