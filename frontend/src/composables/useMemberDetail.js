/*
  会员详情：基础信息 + 名下卡 + 卡模板 + 预约 + 课节/课程/教练映射。
  所有写操作完成后调 reload() 刷新。
*/
import { ref, computed } from 'vue'
import dayjs from 'dayjs'
import api from '../api/client'

export function useMemberDetail(memberId) {
  const member = ref(null)
  const cards = ref([])
  const templates = ref([])
  const bookings = ref([])
  const sessions = ref({}) // sid -> session 对象
  const courses = ref([])
  const coaches = ref([])
  const categories = ref([])

  async function load() {
    // 第一批：会员、卡、卡模板、预约
    const [m, c, t, b] = await Promise.all([
      api.get(`/admin/members/${memberId}`),
      api.get('/admin/cards', { params: { member_id: memberId } }),
      api.get('/admin/card-templates'),
      api.get('/admin/bookings', { params: { member_id: memberId } }),
    ])
    member.value = m
    cards.value = c
    templates.value = t
    bookings.value = b

    // 第二批：相关 sessions（覆盖过去 60 天 + 未来 60 天）+ 课程/教练/类目
    const sids = [...new Set(b.map((x) => x.session_id))]
    const promises = []
    if (sids.length) {
      promises.push(
        api
          .get('/sessions', {
            params: {
              start: dayjs().subtract(60, 'day').toISOString(),
              end: dayjs().add(60, 'day').toISOString(),
            },
          })
          .then((all) => {
            sessions.value = Object.fromEntries(
              all.filter((s) => sids.includes(s.id)).map((s) => [s.id, s]),
            )
          }),
      )
    } else {
      sessions.value = {}
    }
    if (!courses.value.length) promises.push(api.get('/admin/courses').then((d) => (courses.value = d)))
    if (!coaches.value.length) promises.push(api.get('/coaches').then((d) => (coaches.value = d)))
    if (!categories.value.length)
      promises.push(api.get('/admin/course-categories').then((d) => (categories.value = d)))
    await Promise.all(promises)
  }

  // 辅助：把 booking 映射成展示用对象
  const courseName = (cid) => courses.value.find((c) => c.id === cid)?.name || '-'
  const coachTitle = (cid) => coaches.value.find((c) => c.id === cid)?.title || ''

  // 进行中（活跃）预约：booked / waitlist —— 老板代办最常关心的
  const activeBookings = computed(() =>
    bookings.value.filter((b) => ['booked', 'waitlist'].includes(b.status)),
  )

  // 用于表格展示：booking + 拼上 session 详情
  const bookingDisplayList = computed(() => {
    // 优先显示进行中，再按时间倒序补已上课/已取消
    const enriched = bookings.value.map((b) => {
      const s = sessions.value[b.session_id]
      return {
        ...b,
        startAt: s?.start_at,
        courseId: s?.course_id,
        coachId: s?.coach_id,
        room: s?.room,
        courseName: s ? courseName(s.course_id) : '-',
        coachName: s ? coachTitle(s.coach_id) : '',
      }
    })
    // 按 start_at 倒序（无时间的排最后）
    return enriched.sort((a, b) => {
      if (!a.startAt) return 1
      if (!b.startAt) return -1
      return b.startAt.localeCompare(a.startAt)
    })
  })

  return {
    member,
    cards,
    templates,
    bookings,
    sessions,
    courses,
    coaches,
    categories,
    activeBookings,
    bookingDisplayList,
    load,
  }
}
