/*
  排课页面共享：周状态 + 数据加载 + 查找辅助 + 颜色映射。
  把 Sessions.vue 中的纯数据逻辑抽出来，方便测试和复用。
*/
import { ref, computed } from 'vue'
import dayjs from 'dayjs'
import api from '../api/client'
import { colorFor } from './categoryColors.js'

export function useSchedule() {
  const sessions = ref([])
  const courses = ref([])
  const coaches = ref([])
  const categories = ref([])
  const weekOffset = ref(0)
  const loading = ref(false)

  // 周一为周首
  const weekStart = computed(() =>
    dayjs().startOf('week').add(1, 'day').add(weekOffset.value * 7, 'day'),
  )
  const weekEnd = computed(() => weekStart.value.add(7, 'day'))
  const days = computed(() =>
    Array.from({ length: 7 }, (_, i) => weekStart.value.add(i, 'day')),
  )

  async function load() {
    loading.value = true
    try {
      sessions.value = await api.get('/sessions', {
        params: { start: weekStart.value.toISOString(), end: weekEnd.value.toISOString() },
      })
      // 这三个用 client.js 的缓存（30min TTL），首次进页面一次拉，之后切周不再请求
      if (!courses.value.length) courses.value = await api.get('/admin/courses')
      if (!coaches.value.length) coaches.value = await api.get('/coaches')
      if (!categories.value.length) categories.value = await api.get('/admin/course-categories')
    } finally {
      loading.value = false
    }
  }

  const courseName = (id) => courses.value.find((c) => c.id === id)?.name || '-'
  const coachName = (id) => coaches.value.find((c) => c.id === id)?.title || ''

  function colorByCourse(courseId) {
    const course = courses.value.find((c) => c.id === courseId)
    const cat = categories.value.find((c) => c.id === course?.category_id)
    const c = colorFor(cat?.code)
    return { bg: c.soft, bd: c.from }
  }

  // 周视图按天分组（过滤已取消的课节，老板不想看划线版）
  const sessionsByDay = computed(() => {
    const out = {}
    for (const d of days.value) out[d.format('YYYY-MM-DD')] = []
    for (const s of sessions.value) {
      if (s.status === 'cancelled') continue
      const k = dayjs(s.start_at).format('YYYY-MM-DD')
      if (k in out) out[k].push(s)
    }
    return out
  })

  function prevWeek() {
    weekOffset.value--
  }
  function nextWeek() {
    weekOffset.value++
  }
  function thisWeek() {
    weekOffset.value = 0
  }

  return {
    // state
    sessions,
    courses,
    coaches,
    categories,
    weekOffset,
    loading,
    // derived
    weekStart,
    weekEnd,
    days,
    sessionsByDay,
    // helpers
    courseName,
    coachName,
    colorByCourse,
    // actions
    load,
    prevWeek,
    nextWeek,
    thisWeek,
  }
}
