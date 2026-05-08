<script setup>
import { onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import Icon from '../components/Icon.vue'
import { prefetchMobile } from '../composables/prefetchRoutes.js'
const router = useRouter()
const route = useRoute()
onMounted(() => prefetchMobile())

const TABS = [
  { name: 'home',         icon: 'home',           label: '首页' },
  { name: 'schedule',     icon: 'calendar-days',  label: '课表' },
  { name: 'my-bookings',  icon: 'bookmark',       label: '预约' },
  { name: 'my-cards',     icon: 'wallet',         label: '卡包' },
  { name: 'my',           icon: 'user',           label: '我的' },
]
const active = () => route.path.split('/').pop()
function go(name) { router.push('/m/' + name) }
</script>

<template>
  <div class="m-wrap">
    <router-view v-slot="{ Component, route }">
      <keep-alive :max="15">
        <component :is="Component" :key="route.fullPath" />
      </keep-alive>
    </router-view>
    <nav class="tabbar">
      <div
v-for="t in TABS" :key="t.name"
           class="tab" :class="{ active: active() === t.name }"
           @click="go(t.name)">
        <Icon :name="t.icon" :size="20" :stroke="active() === t.name ? 2 : 1.5" />
        <div class="lbl">{{ t.label }}</div>
      </div>
    </nav>
  </div>
</template>

<style scoped>
.m-wrap {
  min-height: 100vh;
  padding-bottom: 64px;
  background: var(--ys-bg);
}
.tabbar {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-top: 1px solid var(--ys-line);
  padding: 6px 0 max(6px, env(safe-area-inset-bottom));
  z-index: 100;
}
.tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 6px 0;
  color: var(--ys-text-muted);
  cursor: pointer;
  transition: color 0.12s;
}
.tab.active { color: var(--ys-primary-deep); }
.lbl { font-size: 10px; letter-spacing: 1px; }
</style>
