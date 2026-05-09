import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuth } from '../stores/auth'

const SITE = '云舍约课'

// 根路径按已登录用户的角色决定默认入口：
//   未登录 → 登录页
//   admin/staff/coach → 后台
//   member 或解析失败 → H5 会员端
// 不能在这里 useAuth()，因为 router 实例创建时 pinia 还没装上，直接读 localStorage。
function rootRedirect() {
  const raw = localStorage.getItem('user')
  if (!raw) return '/login'
  try {
    const user = JSON.parse(raw)
    if (['admin', 'staff', 'coach'].includes(user?.role)) return '/admin/dashboard'
    return '/m/home'
  } catch {
    return '/login'
  }
}

const routes = [
  { path: '/', redirect: rootRedirect },
  { path: '/login', component: () => import('../pages/Login.vue'), meta: { title: '登录' } },

  {
    path: '/admin',
    component: () => import('../layouts/AdminLayout.vue'),
    meta: { requireStaff: true },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', component: () => import('../pages/admin/Dashboard.vue'), meta: { title: '仪表盘' } },
      { path: 'reports', component: () => import('../pages/admin/Reports.vue'), meta: { title: '报表中心' } },
      { path: 'members', component: () => import('../pages/admin/Members.vue'), meta: { title: '会员管理' } },
      { path: 'members/:id', component: () => import('../pages/admin/MemberDetail.vue'), props: true, meta: { title: '会员详情' } },
      { path: 'cards', component: () => import('../pages/admin/Cards.vue'), meta: { title: '卡种' } },
      { path: 'courses', component: () => import('../pages/admin/Courses.vue'), meta: { title: '课程' } },
      { path: 'coaches', component: () => import('../pages/admin/Coaches.vue'), meta: { title: '教练' } },
      { path: 'payroll', component: () => import('../pages/admin/Payroll.vue'), meta: { title: '薪酬结算' } },
      { path: 'at-risk', component: () => import('../pages/admin/AtRisk.vue'), meta: { title: '流失预警' } },
      { path: 'birthday', component: () => import('../pages/admin/Birthday.vue'), meta: { title: '生日礼遇' } },
      { path: 'backups', component: () => import('../pages/admin/Backups.vue'), meta: { title: '备份' } },
      { path: 'pending-orders', component: () => import('../pages/admin/PendingOrders.vue'), meta: { title: '待审订单' } },
      { path: 'staff', component: () => import('../pages/admin/Staff.vue'), meta: { title: '员工' } },
      { path: 'sessions', component: () => import('../pages/admin/Sessions.vue'), meta: { title: '排课' } },
      { path: 'check-in', component: () => import('../pages/admin/CheckIn.vue'), meta: { title: '今日签到' } },
      { path: 'coupons', component: () => import('../pages/admin/Coupons.vue'), meta: { title: '优惠券' } },
      { path: 'settings', component: () => import('../pages/admin/Settings.vue'), meta: { title: '设置' } },
      { path: 'audit-logs', component: () => import('../pages/admin/AuditLogs.vue'), meta: { title: '操作日志' } },
    ],
  },

  {
    path: '/m',
    component: () => import('../layouts/MobileLayout.vue'),
    meta: { requireAuth: true },
    children: [
      { path: '', redirect: '/m/home' },
      { path: 'home', component: () => import('../pages/m/Home.vue'), meta: { title: '首页' } },
      { path: 'schedule', component: () => import('../pages/m/Schedule.vue'), meta: { title: '课表' } },
      { path: 'course/:id', component: () => import('../pages/m/CourseDetail.vue'), props: true, meta: { title: '课程详情' } },
      { path: 'coach/:id', component: () => import('../pages/m/CoachProfile.vue'), props: true, meta: { title: '教练' } },
      { path: 'buy-card', component: () => import('../pages/m/BuyCard.vue'), meta: { title: '购卡' } },
      { path: 'my-orders', component: () => import('../pages/m/MyOrders.vue'), meta: { title: '我的订单' } },
      { path: 'my-bookings', component: () => import('../pages/m/MyBookings.vue'), meta: { title: '我的预约' } },
      { path: 'my-cards', component: () => import('../pages/m/MyCards.vue'), meta: { title: '我的卡包' } },
      { path: 'my-coupons', component: () => import('../pages/m/MyCoupons.vue'), meta: { title: '我的优惠券' } },
      { path: 'my', component: () => import('../pages/m/My.vue'), meta: { title: '个人中心' } },
    ],
  },

  // 兜底 404 → 首页
  { path: '/:pathMatch(.*)*', redirect: '/m/home' },
]

const router = createRouter({ history: createWebHashHistory(), routes })

router.beforeEach((to) => {
  const auth = useAuth()
  if (to.meta.requireAuth && !auth.isLoggedIn) return '/login'
  if (to.meta.requireStaff && !auth.isStaff) {
    if (auth.isLoggedIn) return '/m/schedule'
    return '/login'
  }
})

router.afterEach((to) => {
  const t = to.meta?.title
  document.title = t ? `${t} · ${SITE}` : SITE
})

export default router
