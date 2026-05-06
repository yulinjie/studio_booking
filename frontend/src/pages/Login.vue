<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuth } from '../stores/auth'
import StudioLogo from '../components/StudioLogo.vue'

const auth = useAuth()
const router = useRouter()
const route = useRoute()
const mode = ref('login')
const phone = ref('')
const password = ref('')
const name = ref('')
const loading = ref(false)
const err = ref('')

onMounted(() => {
  if (route.query.mode === 'register') mode.value = 'register'
})

async function submit() {
  err.value = ''
  loading.value = true
  try {
    let user
    if (mode.value === 'login') {
      user = await auth.login(phone.value, password.value)
    } else {
      user = await auth.register(phone.value, password.value, name.value || phone.value)
    }
    if (['admin', 'staff', 'coach'].includes(user.role)) {
      router.replace('/admin/dashboard')
    } else {
      router.replace('/m/schedule')
    }
  } catch (e) {
    err.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <div class="bg-deco">
      <div class="circle c1"></div>
      <div class="circle c2"></div>
      <div class="circle c3"></div>
    </div>

    <div class="login-card">
      <div class="brand">
        <StudioLogo size="lg" />
      </div>

      <p class="welcome">{{ mode === 'login' ? '欢迎回来' : '加入云舍' }}</p>
      <p class="welcome-sub">{{ mode === 'login' ? '请用手机号登录账户' : '一起开始你的练习' }}</p>

      <el-form @submit.prevent="submit" size="large" class="form">
        <el-form-item>
          <el-input v-model="phone" placeholder="手机号" autocomplete="tel">
            <template #prefix><span class="prefix-icon">📱</span></template>
          </el-input>
        </el-form-item>
        <el-form-item v-if="mode === 'register'">
          <el-input v-model="name" placeholder="姓名">
            <template #prefix><span class="prefix-icon">👤</span></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-input v-model="password" type="password" placeholder="密码" autocomplete="current-password" show-password>
            <template #prefix><span class="prefix-icon">🔒</span></template>
          </el-input>
        </el-form-item>
        <el-alert v-if="err" :title="err" type="error" :closable="false" show-icon class="err" />
        <el-button type="primary" :loading="loading" @click="submit" class="submit-btn">
          {{ mode === 'login' ? '登 录' : '注册并登录' }}
        </el-button>
      </el-form>

      <div class="switch-mode">
        <el-button link type="primary" @click="mode = mode === 'login' ? 'register' : 'login'">
          {{ mode === 'login' ? '还没账号？立即注册' : '已有账号，去登录' }}
        </el-button>
      </div>
    </div>

    <div class="footer-tag">© 云舍 · 安静地练习</div>
  </div>
</template>

<style scoped>
.login-wrap {
  min-height: 100vh;
  background: linear-gradient(160deg, #EFEAE0 0%, #E2DDD0 50%, #DDE5DC 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 20px 60px;
  position: relative;
  overflow: hidden;
}
.bg-deco { position: absolute; inset: 0; pointer-events: none; }
.bg-deco .circle {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.5;
}
.bg-deco .c1 {
  width: 300px; height: 300px;
  background: #B5C4A7;
  top: -80px; left: -60px;
}
.bg-deco .c2 {
  width: 360px; height: 360px;
  background: #DCC5C6;
  bottom: -120px; right: -100px;
}
.bg-deco .c3 {
  width: 200px; height: 200px;
  background: #E5DCC6;
  top: 40%; left: 60%;
}

.login-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 380px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 20px;
  box-shadow: 0 24px 60px rgba(63, 60, 58, 0.12);
  padding: 40px 32px 32px;
}

.brand {
  text-align: center;
  margin-bottom: 28px;
}
.welcome {
  text-align: center;
  font-size: 18px;
  font-weight: 400;
  color: var(--ys-text);
  margin: 0;
  letter-spacing: 1px;
}
.welcome-sub {
  text-align: center;
  font-size: 13px;
  color: var(--ys-text-muted);
  margin: 4px 0 24px;
  letter-spacing: 0.5px;
}
.prefix-icon {
  margin-right: 4px;
  opacity: 0.6;
}
.form { display: flex; flex-direction: column; gap: 0; }
.err { margin-bottom: 12px; border-radius: var(--ys-radius-sm) !important; }
.submit-btn {
  width: 100%;
  height: 46px;
  font-size: 15px;
  letter-spacing: 4px;
  border-radius: var(--ys-radius) !important;
}
.switch-mode {
  text-align: center;
  margin-top: 18px;
}
.footer-tag {
  position: absolute;
  bottom: 24px;
  font-size: 11px;
  color: var(--ys-text-muted);
  letter-spacing: 4px;
}
</style>
