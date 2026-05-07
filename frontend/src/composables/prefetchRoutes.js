/*
  在首屏渲染完成 + idle 之后，后台偷偷把同 layout 下的所有路由 chunk 都拉下来缓存。
  这样切 tab 时 chunk 已在浏览器缓存里，不再付 RTT。

  使用：在 AdminLayout / MobileLayout mounted 后调用 prefetchAdmin() / prefetchMobile()
*/

const ADMIN_LOADERS = [
  () => import('../pages/admin/Dashboard.vue'),
  () => import('../pages/admin/CheckIn.vue'),
  () => import('../pages/admin/Sessions.vue'),
  () => import('../pages/admin/Reports.vue'),
  () => import('../pages/admin/Payroll.vue'),
  () => import('../pages/admin/Members.vue'),
  () => import('../pages/admin/MemberDetail.vue'),
  () => import('../pages/admin/AtRisk.vue'),
  () => import('../pages/admin/Birthday.vue'),
  () => import('../pages/admin/Coaches.vue'),
  () => import('../pages/admin/Cards.vue'),
  () => import('../pages/admin/Courses.vue'),
  () => import('../pages/admin/Coupons.vue'),
  () => import('../pages/admin/Settings.vue'),
  () => import('../pages/admin/AuditLogs.vue'),
  () => import('../pages/admin/Backups.vue'),
  () => import('../pages/admin/PendingOrders.vue'),
]

const MOBILE_LOADERS = [
  () => import('../pages/m/Home.vue'),
  () => import('../pages/m/Schedule.vue'),
  () => import('../pages/m/MyBookings.vue'),
  () => import('../pages/m/MyCards.vue'),
  () => import('../pages/m/MyCoupons.vue'),
  () => import('../pages/m/My.vue'),
  () => import('../pages/m/CoachProfile.vue'),
  () => import('../pages/m/CourseDetail.vue'),
  () => import('../pages/m/BuyCard.vue'),
  () => import('../pages/m/MyOrders.vue'),
]

function whenIdle(cb, timeout = 1500) {
  if (window.requestIdleCallback) {
    window.requestIdleCallback(cb, { timeout })
  } else {
    setTimeout(cb, 1000)
  }
}

function prefetchAll(loaders) {
  // 串行而非并行，避免一次性吃光带宽影响 API
  let i = 0
  function next() {
    if (i >= loaders.length) return
    const fn = loaders[i++]
    try {
      fn().catch(() => {}).finally(() => setTimeout(next, 80))
    } catch { setTimeout(next, 80) }
  }
  whenIdle(next)
}

export function prefetchAdmin() { prefetchAll(ADMIN_LOADERS) }
export function prefetchMobile() { prefetchAll(MOBILE_LOADERS) }
