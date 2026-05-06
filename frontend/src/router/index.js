import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuth } from '../stores/auth'

const routes = [
  { path: '/', redirect: '/m/home' },
  { path: '/login', component: () => import('../pages/Login.vue') },

  {
    path: '/admin',
    component: () => import('../layouts/AdminLayout.vue'),
    meta: { requireStaff: true },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', component: () => import('../pages/admin/Dashboard.vue') },
      { path: 'reports', component: () => import('../pages/admin/Reports.vue') },
      { path: 'members', component: () => import('../pages/admin/Members.vue') },
      { path: 'members/:id', component: () => import('../pages/admin/MemberDetail.vue'), props: true },
      { path: 'cards', component: () => import('../pages/admin/Cards.vue') },
      { path: 'courses', component: () => import('../pages/admin/Courses.vue') },
      { path: 'coaches', component: () => import('../pages/admin/Coaches.vue') },
      { path: 'payroll', component: () => import('../pages/admin/Payroll.vue') },
      { path: 'at-risk', component: () => import('../pages/admin/AtRisk.vue') },
      { path: 'birthday', component: () => import('../pages/admin/Birthday.vue') },
      { path: 'backups', component: () => import('../pages/admin/Backups.vue') },
      { path: 'sessions', component: () => import('../pages/admin/Sessions.vue') },
      { path: 'check-in', component: () => import('../pages/admin/CheckIn.vue') },
      { path: 'coupons', component: () => import('../pages/admin/Coupons.vue') },
      { path: 'settings', component: () => import('../pages/admin/Settings.vue') },
      { path: 'audit-logs', component: () => import('../pages/admin/AuditLogs.vue') },
    ],
  },

  {
    path: '/m',
    component: () => import('../layouts/MobileLayout.vue'),
    meta: { requireAuth: true },
    children: [
      { path: '', redirect: '/m/home' },
      { path: 'home', component: () => import('../pages/m/Home.vue') },
      { path: 'schedule', component: () => import('../pages/m/Schedule.vue') },
      { path: 'course/:id', component: () => import('../pages/m/CourseDetail.vue'), props: true },
      { path: 'coach/:id', component: () => import('../pages/m/CoachProfile.vue'), props: true },
      { path: 'my-bookings', component: () => import('../pages/m/MyBookings.vue') },
      { path: 'my-cards', component: () => import('../pages/m/MyCards.vue') },
      { path: 'my-coupons', component: () => import('../pages/m/MyCoupons.vue') },
      { path: 'my', component: () => import('../pages/m/My.vue') },
    ],
  },
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

export default router
