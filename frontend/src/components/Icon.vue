<script setup>
// 统一 SVG 图标包装。用法：<Icon name="calendar-days" :size="18" />
import * as icons from 'lucide-vue-next'
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 18 },
  stroke: { type: [Number, String], default: 1.6 },
  color: { type: String, default: 'currentColor' },
})

function toPascal(s) {
  return s.split('-').map(w => w[0].toUpperCase() + w.slice(1)).join('')
}

const Cmp = computed(() => icons[toPascal(props.name)] || icons.Circle)
</script>

<template>
  <component :is="Cmp" :size="size" :stroke-width="stroke" :color="color" />
</template>
