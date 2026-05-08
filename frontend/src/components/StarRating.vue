<script setup>
const props = defineProps({
  value: { type: Number, default: 0 },
  max: { type: Number, default: 5 },
  size: { type: Number, default: 16 },
  readonly: { type: Boolean, default: false },
  color: { type: String, default: '#C8A48C' },   // 焦糖色
})
const emit = defineEmits(['update:value'])
function set(n) { if (!props.readonly) emit('update:value', n) }
</script>

<template>
  <div class="star-row" :style="{ '--size': size + 'px', '--c': color }">
    <span
v-for="i in max" :key="i"
          class="star"
          :class="{ on: i <= value, click: !readonly }"
          @click="set(i)">★</span>
  </div>
</template>

<style scoped>
.star-row { display: inline-flex; gap: 2px; line-height: 1; }
.star {
  font-size: var(--size);
  color: #DDD7CC;
  transition: color 0.1s;
}
.star.on { color: var(--c); }
.star.click { cursor: pointer; }
.star.click:hover { transform: scale(1.1); }
</style>
