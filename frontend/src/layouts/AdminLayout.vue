<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuth } from '../stores/auth'
import { useRouter } from 'vue-router'
import api from '../api/client'
import StudioLogo from '../components/StudioLogo.vue'
import Icon from '../components/Icon.vue'

const auth = useAuth()
const router = useRouter()

const showPwd = ref(false)
const pwdForm = ref({ old_password: '', new_password: '', confirm: '' })
const pwdSaving = ref(false)

async function changePassword() {
  if (pwdForm.value.new_password !== pwdForm.value.confirm) return ElMessage.error('两次新密码不一致')
  if (pwdForm.value.new_password.length < 4) return ElMessage.error('新密码至少 4 位')
  pwdSaving.value = true
  try {
    await api.post('/me/change-password', { old_password: pwdForm.value.old_password, new_password: pwdForm.value.new_password })
    ElMessage.success('密码已修改，请重新登录')
    auth.logout(); router.replace('/login')
  } catch (e) { ElMessage.error(e.message) } finally {
    pwdSaving.value = false
    showPwd.value = false
    pwdForm.value = { old_password: '', new_password: '', confirm: '' }
  }
}
function logout() { auth.logout(); router.replace('/login') }

const NAV = [
  { group: '运营', items: [
    { path: '/admin/dashboard',   icon: 'layout-dashboard',  label: '概览' },
    { path: '/admin/check-in',    icon: 'check-circle-2',    label: '今日签到' },
    { path: '/admin/sessions',    icon: 'calendar-days',     label: '排课' },
    { path: '/admin/reports',     icon: 'trending-up',       label: '报表' },
    { path: '/admin/payroll',     icon: 'banknote',          label: '工资条' },
  ]},
  { group: '管理', items: [
    { path: '/admin/members',     icon: 'users',             label: '会员' },
    { path: '/admin/coaches',     icon: 'user-cog',          label: '教练' },
    { path: '/admin/cards',       icon: 'credit-card',       label: '卡种' },
    { path: '/admin/courses',     icon: 'book-open',         label: '课程' },
    { path: '/admin/coupons',     icon: 'ticket-percent',    label: '优惠券' },
  ]},
  { group: '系统', items: [
    { path: '/admin/settings',    icon: 'settings',          label: '设置' },
    { path: '/admin/audit-logs',  icon: 'scroll-text',       label: '操作日志' },
  ]},
]
</script>

<template>
  <el-container class="admin-container">
    <el-aside width="220px" class="aside">
      <div class="logo-area">
        <StudioLogo size="sm" />
      </div>
      <nav class="nav">
        <template v-for="g in NAV" :key="g.group">
          <div class="nav-group">{{ g.group }}</div>
          <router-link v-for="n in g.items" :key="n.path" :to="n.path" class="nav-item" active-class="active">
            <Icon :name="n.icon" :size="16" :stroke="1.6" />
            <span>{{ n.label }}</span>
          </router-link>
        </template>
      </nav>
      <div class="aside-footer">云舍 · 后台 v1.0</div>
    </el-aside>

    <el-container>
      <el-header class="topbar">
        <div class="crumb">{{ $route.path.split('/').pop() }}</div>
        <div class="user">
          <span class="user-name">{{ auth.user?.name }}</span>
          <span class="user-role">{{ auth.user?.role }}</span>
          <el-divider direction="vertical" />
          <el-button size="small" link @click="showPwd = true">修改密码</el-button>
          <el-button size="small" link @click="logout">退出</el-button>
        </div>
      </el-header>
      <el-main class="main"><router-view /></el-main>
    </el-container>
  </el-container>

  <el-dialog v-model="showPwd" title="修改密码" width="400px">
    <el-form label-width="90px">
      <el-form-item label="原密码"><el-input v-model="pwdForm.old_password" type="password" show-password /></el-form-item>
      <el-form-item label="新密码"><el-input v-model="pwdForm.new_password" type="password" show-password /></el-form-item>
      <el-form-item label="确认新密码"><el-input v-model="pwdForm.confirm" type="password" show-password /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showPwd = false">取消</el-button>
      <el-button type="primary" :loading="pwdSaving" @click="changePassword">确认修改</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.admin-container { height: 100vh; background: var(--ys-bg); }
.aside {
  background: linear-gradient(180deg, #FFFFFF 0%, #F7F3EC 100%);
  border-right: 1px solid var(--ys-line);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.logo-area {
  padding: 22px 0 18px;
  display: flex;
  justify-content: center;
  border-bottom: 1px solid var(--ys-line);
}
.nav {
  flex: 1;
  padding: 14px 12px;
  overflow-y: auto;
}
.nav-group {
  font-size: 10px;
  color: var(--ys-text-light);
  letter-spacing: 4px;
  padding: 12px 14px 6px;
  font-weight: 500;
}
.nav-group:first-child { padding-top: 4px; }
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 9px 14px;
  border-radius: 8px;
  color: var(--ys-text-soft);
  text-decoration: none;
  font-size: 14px;
  letter-spacing: 0.5px;
  transition: all 0.15s;
}
.nav-item:hover { background: var(--ys-bg-soft); color: var(--ys-text); }
.nav-item.active {
  background: var(--ys-primary-bg);
  color: var(--ys-primary-deep);
  font-weight: 500;
}
.aside-footer {
  padding: 14px;
  font-size: 11px;
  color: var(--ys-text-light);
  text-align: center;
  letter-spacing: 2px;
  border-top: 1px solid var(--ys-line);
}
.topbar {
  background: var(--ys-bg-card);
  border-bottom: 1px solid var(--ys-line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
}
.crumb { font-size: 13px; color: var(--ys-text-muted); letter-spacing: 1px; text-transform: capitalize; }
.user { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.user-name { color: var(--ys-text); font-weight: 500; }
.user-role { display: inline-block; margin-left: 6px; padding: 2px 8px; background: var(--ys-bg-soft); border-radius: 4px; font-size: 11px; color: var(--ys-text-muted); letter-spacing: 1px; }
.main { padding: 24px; background: var(--ys-bg); }
</style>
