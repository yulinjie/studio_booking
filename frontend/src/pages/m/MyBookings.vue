<script setup>
import { ref, onMounted, computed } from 'vue'
import { showDialog, showSuccessToast, showFailToast, showToast } from 'vant'
import api from '../../api/client'
import dayjs from 'dayjs'
import StarRating from '../../components/StarRating.vue'
import EmptyState from '../../components/EmptyState.vue'
import Icon from '../../components/Icon.vue'

const tab = ref('upcoming')
const bookings = ref([])
const sessions = ref({})
const courses = ref([])
const evaluatedSet = ref(new Set())
const loading = ref(false)

const showEval = ref(false)
const evalForm = ref({ booking_id: null, rating: 5, comment: '', is_anonymous: false, _course: '', _date: '' })

async function load() {
  loading.value = true
  try {
    bookings.value = await api.get('/me/bookings', { params: { upcoming: tab.value === 'upcoming' } })
    if (!courses.value.length) courses.value = await api.get('/courses')
    const sids = [...new Set(bookings.value.map(b => b.session_id))]
    if (sids.length) {
      const all = await api.get('/sessions', {
        params: { start: dayjs().subtract(60, 'day').toISOString(), end: dayjs().add(60, 'day').toISOString() },
      })
      sessions.value = Object.fromEntries(all.filter(s => sids.includes(s.id)).map(s => [s.id, s]))
    }
    // 拉已评价的 booking_id 集合，用于隐藏评价按钮
    try {
      const pending = await api.get('/me/pending-evaluations')
      const pendingIds = new Set(pending.map(b => b.id))
      const attendedIds = bookings.value.filter(b => b.status === 'attended').map(b => b.id)
      evaluatedSet.value = new Set(attendedIds.filter(id => !pendingIds.has(id)))
    } catch {}
  } finally { loading.value = false }
}

onMounted(load)

const courseName = (id) => courses.value.find(c => c.id === id)?.name || '课程'
const sessAt = (sid) => sessions.value[sid]?.start_at
const sessRoom = (sid) => sessions.value[sid]?.room

async function cancel(b) {
  try { await showDialog({ title: '取消预约？', message: '取消后按规则可能不返还卡次', showCancelButton: true, confirmButtonColor: '#C8927E' }) } catch { return }
  try {
    const r = await api.post(`/bookings/${b.id}/cancel`)
    if (r.status === 'late_cancelled') showToast('超时取消，未返还卡次')
    else showSuccessToast('已取消')
    await load()
  } catch (e) { showFailToast(e.message) }
}

function openEval(b) {
  evalForm.value = {
    booking_id: b.id, rating: 5, comment: '', is_anonymous: false,
    _course: courseName(sessions.value[b.session_id]?.course_id),
    _date: sessAt(b.session_id) ? dayjs(sessAt(b.session_id)).format('M-D HH:mm') : '',
  }
  showEval.value = true
}

async function submitEval() {
  try {
    await api.post('/evaluations', {
      booking_id: evalForm.value.booking_id,
      rating: evalForm.value.rating,
      comment: evalForm.value.comment || null,
      is_anonymous: evalForm.value.is_anonymous,
    })
    showSuccessToast('谢谢你的评价')
    showEval.value = false
    await load()
  } catch (e) { showFailToast(e.message) }
}

const STATUS = {
  booked:    { text: '已预约',     bg: '#DDE5DC', color: '#6E7B73', dot: '#88958D' },
  waitlist:  { text: '候补中',     bg: '#FAEEDE', color: '#A4836B', dot: '#C8A48C' },
  attended:  { text: '已上课',     bg: '#E0E8DC', color: '#6E7E63', dot: '#7A9181' },
  cancelled: { text: '已取消',     bg: '#EEEAE2', color: '#9E9890', dot: '#C5BFB6' },
  late_cancelled: { text: '超时取消', bg: '#F2DDD3', color: '#A4654E', dot: '#C8927E' },
  no_show:   { text: '爽约',       bg: '#F2DDD3', color: '#A4654E', dot: '#C8927E' },
}

const grouped = computed(() => {
  const groups = []
  let lastMonth = ''
  for (const b of bookings.value) {
    const m = dayjs(sessAt(b.session_id) || b.booked_at).format('YYYY 年 M 月')
    if (m !== lastMonth) {
      groups.push({ label: m, items: [] })
      lastMonth = m
    }
    groups[groups.length - 1].items.push(b)
  }
  return groups
})

const canEval = (b) => b.status === 'attended' && !evaluatedSet.value.has(b.id)
</script>

<template>
  <div class="page">
    <header class="header">
      <h2>我的预约</h2>
      <p class="sub">{{ tab === 'upcoming' ? '即将开始的课程' : '所有预约记录' }}</p>
    </header>

    <van-tabs v-model:active="tab" @change="load" line-width="32" line-height="2" sticky offset-top="0">
      <van-tab title="即将开始" name="upcoming"></van-tab>
      <van-tab title="历史记录" name="all"></van-tab>
    </van-tabs>

    <EmptyState v-if="!bookings.length && !loading" illust="bookmark"
      :title="tab === 'upcoming' ? '没有待上的课' : '没有预约记录'"
      :sub="tab === 'upcoming' ? '去课表预约第一节课吧' : ''" />

    <div v-for="g in grouped" :key="g.label" class="month">
      <div class="month-label">{{ g.label }}</div>
      <div v-for="b in g.items" :key="b.id" class="b-card">
        <div class="status-stripe" :style="{ background: STATUS[b.status]?.dot || '#CCC' }"></div>
        <div class="b-body">
          <div class="b-row">
            <span class="b-title">{{ courseName(sessions[b.session_id]?.course_id) }}</span>
            <span class="b-status" :style="{ background: STATUS[b.status]?.bg, color: STATUS[b.status]?.color }">
              {{ STATUS[b.status]?.text || b.status }}
              <em v-if="b.waitlist_order">#{{ b.waitlist_order }}</em>
            </span>
          </div>
          <div class="b-meta">
            <Icon name="clock" :size="11" />
            <span v-if="sessAt(b.session_id)">{{ dayjs(sessAt(b.session_id)).format('M月D日 ddd HH:mm') }}</span>
          </div>
          <div class="b-meta" v-if="sessRoom(b.session_id)">
            <Icon name="map-pin" :size="11" />
            <span>{{ sessRoom(b.session_id) }}</span>
          </div>
          <div class="b-actions" v-if="['booked','waitlist'].includes(b.status) || canEval(b) || (b.status === 'attended' && evaluatedSet.has(b.id))">
            <span v-if="b.status === 'attended' && evaluatedSet.has(b.id)" class="evaluated-tag">
              <Icon name="check-circle-2" :size="11" /> 已评价
            </span>
            <van-button v-if="canEval(b)" size="mini" type="primary" round @click="openEval(b)">
              <Icon name="star" :size="11" /> 评价
            </van-button>
            <van-button v-if="['booked','waitlist'].includes(b.status)" size="mini" plain type="danger" round @click="cancel(b)">取消预约</van-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 评价弹窗 -->
    <van-popup v-model:show="showEval" position="bottom" round closeable :style="{ height: '64%' }">
      <div class="eval-pop">
        <h3>你的反馈</h3>
        <p class="eval-sub">{{ evalForm._course }} · {{ evalForm._date }}</p>

        <div class="rate-block">
          <div class="rate-label">本次课程感受</div>
          <div class="rate-stars">
            <StarRating v-model:value="evalForm.rating" :size="32" />
          </div>
          <div class="rate-text">{{ ['很糟','一般','还行','不错','超棒'][evalForm.rating - 1] }}</div>
        </div>

        <div class="comment-block">
          <div class="rate-label">想说点什么？（可选）</div>
          <textarea
            v-model="evalForm.comment"
            class="comment-input"
            placeholder="教练讲解清晰 / 强度合适 / 体式调整很到位..."
            rows="4"
            maxlength="500"></textarea>
          <div class="char-count">{{ (evalForm.comment || '').length }} / 500</div>
        </div>

        <label class="anon">
          <input type="checkbox" v-model="evalForm.is_anonymous" />
          <span>匿名提交（教练看不到我的姓名）</span>
        </label>

        <van-button block type="primary" round @click="submitEval">提交评价</van-button>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.page { padding-bottom: 20px; }
.header { padding: 22px 20px 6px; }
.header h2 { margin: 0; font-size: 22px; font-weight: 500; letter-spacing: 1px; }
.header .sub { color: var(--ys-text-muted); margin: 4px 0 0; font-size: 13px; }

:deep(.van-tabs__wrap) { background: var(--ys-bg); border-bottom: 1px solid var(--ys-line); }

.month { padding: 16px 16px 0; }
.month-label { font-size: 11px; color: var(--ys-text-muted); letter-spacing: 4px; margin-bottom: 8px; padding-left: 4px; }

.b-card {
  background: var(--ys-bg-card);
  border-radius: var(--ys-radius);
  margin-bottom: 10px;
  display: flex;
  overflow: hidden;
  box-shadow: var(--ys-shadow-sm);
  border: 1px solid var(--ys-line);
}
.status-stripe { width: 4px; flex: none; }
.b-body { flex: 1; padding: 14px; }
.b-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 4px; }
.b-title { font-size: 15px; font-weight: 500; color: var(--ys-text); }
.b-status { font-size: 11px; padding: 3px 10px; border-radius: 10px; letter-spacing: 0.5px; white-space: nowrap; }
.b-status em { font-style: normal; margin-left: 2px; opacity: 0.75; }
.b-meta {
  font-size: 12px;
  color: var(--ys-text-muted);
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.b-actions {
  margin-top: 10px;
  display: flex;
  gap: 6px;
  align-items: center;
  justify-content: flex-end;
}
.evaluated-tag {
  font-size: 11px;
  color: var(--ys-success);
  display: inline-flex;
  align-items: center;
  gap: 3px;
  letter-spacing: 1px;
}

/* Eval popup */
.eval-pop { padding: 28px 22px 30px; }
.eval-pop h3 { margin: 0; font-size: 18px; font-weight: 500; letter-spacing: 1px; text-align: center; }
.eval-sub { text-align: center; color: var(--ys-text-muted); font-size: 12px; margin: 6px 0 24px; letter-spacing: 1px; }

.rate-block { text-align: center; margin-bottom: 20px; }
.rate-label { font-size: 11px; color: var(--ys-text-muted); letter-spacing: 2px; margin-bottom: 12px; }
.rate-stars { display: flex; justify-content: center; }
.rate-text {
  margin-top: 12px;
  font-size: 13px;
  color: var(--ys-accent-deep);
  letter-spacing: 2px;
}

.comment-block { margin-bottom: 16px; }
.comment-input {
  width: 100%;
  border: 1px solid var(--ys-line);
  background: var(--ys-bg-soft);
  border-radius: var(--ys-radius);
  padding: 10px 12px;
  font-size: 13px;
  font-family: inherit;
  resize: none;
  outline: none;
  color: var(--ys-text);
  box-sizing: border-box;
}
.comment-input:focus { border-color: var(--ys-primary); }
.char-count {
  text-align: right;
  font-size: 11px;
  color: var(--ys-text-light);
  margin-top: 4px;
}

.anon {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--ys-text-soft);
  margin-bottom: 18px;
  cursor: pointer;
}
.anon input { accent-color: var(--ys-primary); }
</style>
