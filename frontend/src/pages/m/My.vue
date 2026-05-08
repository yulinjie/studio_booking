<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showSuccessToast, showFailToast, showDialog } from 'vant'
import api from '../../api/client'
import { useAuth } from '../../stores/auth'
import GrowthPanel from '../../components/GrowthPanel.vue'

const router = useRouter()
const auth = useAuth()
const me = ref(null)
const editing = ref(false)
const form = ref({})
const showPwd = ref(false)
const pwd = ref({ old_password: '', new_password: '', confirm: '' })

async function load() {
  me.value = await api.get('/auth/me')
  form.value = {
    name: me.value.name,
    gender: me.value.gender || '',
    emergency_contact_name: me.value.emergency_contact_name || '',
    emergency_contact_phone: me.value.emergency_contact_phone || '',
    health_note: me.value.health_note || '',
  }
}

async function save() {
  try {
    me.value = await api.patch('/me', form.value)
    auth.user = { ...auth.user, ...me.value }
    localStorage.setItem('user', JSON.stringify(auth.user))
    editing.value = false
    showSuccessToast('已保存')
  } catch (e) { showFailToast(e.message) }
}

async function changePassword() {
  if (pwd.value.new_password !== pwd.value.confirm) return showFailToast('两次新密码不一致')
  if (pwd.value.new_password.length < 4) return showFailToast('新密码至少 4 位')
  try {
    await api.post('/me/change-password', { old_password: pwd.value.old_password, new_password: pwd.value.new_password })
    showSuccessToast('已修改，请重新登录')
    setTimeout(() => { auth.logout(); router.replace('/login') }, 800)
  } catch (e) { showFailToast(e.message) }
}

async function logout() {
  try { await showDialog({ title: '退出登录？', showCancelButton: true, confirmButtonColor: '#88958D' }) } catch { return }
  auth.logout()
  router.replace('/login')
}

const initial = (n) => (n?.[0] || '?').toUpperCase()

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="hero">
      <div class="hero-bg">
        <div class="bb b1"></div>
        <div class="bb b2"></div>
      </div>
      <div class="profile">
        <div class="avatar">{{ initial(me?.name) }}</div>
        <div class="name">{{ me?.name }}</div>
        <div class="phone">{{ me?.phone }}</div>
        <div v-if="me?.health_note" class="health-tag">⚕ 已记录健康备注</div>
      </div>
    </div>

    <div v-if="!editing" class="section">
      <div class="section-title">成长</div>
      <GrowthPanel />
    </div>

    <div v-if="!editing" class="section">
      <div class="section-title">资料</div>
      <div class="cell-group">
        <div class="cell" @click="editing = true">
          <span class="cell-label">性别</span>
          <span class="cell-value">{{ me?.gender || '未填' }}</span>
        </div>
        <div class="cell" @click="editing = true">
          <span class="cell-label">紧急联系人</span>
          <span class="cell-value">{{ me?.emergency_contact_name || '未填' }}</span>
        </div>
        <div class="cell" @click="editing = true">
          <span class="cell-label">紧急电话</span>
          <span class="cell-value">{{ me?.emergency_contact_phone || '未填' }}</span>
        </div>
        <div class="cell cell-multi" @click="editing = true">
          <span class="cell-label">健康备注</span>
          <span class="cell-value-multi">{{ me?.health_note || '建议填写已知伤病或不能做的动作' }}</span>
        </div>
      </div>
      <div class="hint">点击任意一项可编辑 ›</div>
    </div>

    <div v-else class="section">
      <div class="section-title">编辑资料</div>
      <van-cell-group inset>
        <van-field v-model="form.name" label="姓名" />
        <van-field v-model="form.gender" label="性别" placeholder="女 / 男" />
        <van-field v-model="form.emergency_contact_name" label="紧急联系人" placeholder="家属姓名" />
        <van-field v-model="form.emergency_contact_phone" label="紧急电话" type="tel" />
        <van-field v-model="form.health_note" label="健康备注" type="textarea" autosize :rows="2" placeholder="已知伤病 / 过敏 / 不能做的动作" />
      </van-cell-group>
      <div class="edit-actions">
        <van-button type="primary" round block @click="save">保存修改</van-button>
        <van-button plain round block style="margin-top: 8px" @click="editing = false; load()">取消</van-button>
      </div>
    </div>

    <div class="section">
      <div class="section-title">账户</div>
      <div class="cell-group">
        <div class="cell action-cell" @click="showPwd = true">
          <span class="cell-label">🔒 修改密码</span>
          <span class="arrow">›</span>
        </div>
        <div class="cell action-cell" @click="logout">
          <span class="cell-label" style="color: var(--ys-danger)">↗ 退出登录</span>
        </div>
      </div>
    </div>

    <div class="footer">© 云舍 · 安静地练习</div>

    <van-dialog v-model:show="showPwd" title="修改密码" show-cancel-button :before-close="(action, done) => { if (action === 'confirm') { changePassword(); done(true) } else { done(true) } }" confirm-button-color="#88958D">
      <van-cell-group>
        <van-field v-model="pwd.old_password" label="原密码" type="password" />
        <van-field v-model="pwd.new_password" label="新密码" type="password" />
        <van-field v-model="pwd.confirm" label="确认新密码" type="password" />
      </van-cell-group>
    </van-dialog>
  </div>
</template>

<style scoped>
.page { padding-bottom: 24px; }

.hero {
  position: relative;
  padding: 36px 20px 32px;
  background: linear-gradient(160deg, #DDE5DC 0%, #EFEAE0 100%);
  overflow: hidden;
}
.hero-bg .bb {
  position: absolute;
  border-radius: 50%;
  filter: blur(40px);
  opacity: 0.5;
}
.bb.b1 { width: 200px; height: 200px; background: #B5C4A7; top: -50px; right: -40px; }
.bb.b2 { width: 160px; height: 160px; background: #DCC5C6; bottom: -40px; left: -30px; }
.profile { position: relative; text-align: center; }
.avatar {
  width: 72px; height: 72px;
  border-radius: 50%;
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1.5px solid rgba(255,255,255,0.6);
  margin: 0 auto 12px;
  line-height: 70px;
  font-size: 28px;
  color: var(--ys-text-soft);
  letter-spacing: 1px;
  font-weight: 300;
  box-shadow: 0 4px 16px rgba(63,60,58,0.06);
}
.name {
  font-size: 18px;
  letter-spacing: 2px;
  color: var(--ys-text);
  font-weight: 400;
}
.phone {
  font-size: 12px;
  color: var(--ys-text-muted);
  letter-spacing: 1.5px;
  margin-top: 4px;
  font-variant-numeric: tabular-nums;
}
.health-tag {
  display: inline-block;
  margin-top: 12px;
  font-size: 11px;
  color: var(--ys-warning);
  background: rgba(217,185,143,0.18);
  padding: 4px 12px;
  border-radius: 12px;
  letter-spacing: 1px;
}

.section { padding: 18px 16px 0; }
.section-title {
  font-size: 11px;
  color: var(--ys-text-muted);
  letter-spacing: 4px;
  margin: 0 4px 8px;
}

.cell-group {
  background: var(--ys-bg-card);
  border-radius: var(--ys-radius);
  overflow: hidden;
  box-shadow: var(--ys-shadow-sm);
}
.cell {
  padding: 14px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--ys-line);
  cursor: pointer;
}
.cell:last-child { border-bottom: 0; }
.cell-label { font-size: 14px; color: var(--ys-text); }
.cell-value { font-size: 13px; color: var(--ys-text-muted); }
.cell-multi { flex-direction: column; align-items: flex-start; gap: 4px; }
.cell-value-multi { font-size: 12px; color: var(--ys-text-muted); line-height: 1.6; }
.action-cell:hover { background: var(--ys-bg-soft); }
.arrow { color: var(--ys-text-light); font-size: 18px; line-height: 1; }

.hint {
  font-size: 11px;
  color: var(--ys-text-light);
  text-align: right;
  margin: 6px 8px 0;
}

.edit-actions { padding: 16px 4px; }

.footer {
  text-align: center;
  font-size: 10px;
  color: var(--ys-text-light);
  letter-spacing: 4px;
  padding: 30px 0 0;
}
</style>
