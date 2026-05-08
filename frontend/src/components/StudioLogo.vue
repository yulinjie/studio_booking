<script setup>
defineProps({
  size: { type: String, default: 'md' },     // sm | md | lg
  inverse: { type: Boolean, default: false },
  showTag: { type: Boolean, default: true },
})
</script>

<template>
  <div class="studio-logo" :class="[`size-${size}`, { inverse }]">
    <div class="mark">
      <svg viewBox="0 0 40 40" class="cloud-svg" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path
d="M8 24 Q4 24 4 20 Q4 16 8 16 Q8 11 14 11 Q19 11 21 14 Q24 12 28 14 Q34 14 34 20 Q38 20 38 24 Q38 28 34 28 L8 28 Q4 28 8 24 Z"
              stroke="currentColor" stroke-width="1.4" fill="none" opacity="0.9"/>
      </svg>
      <span class="chars">云舍</span>
    </div>
    <div v-if="showTag" class="tag">YOGA · PILATES</div>
  </div>
</template>

<style scoped>
.studio-logo {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: var(--ys-text);
  user-select: none;
}
.studio-logo.inverse { color: #F4EFE6; }
.mark {
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}
.cloud-svg {
  flex: none;
}
.chars {
  font-weight: 300;
  letter-spacing: 0.5em;
  padding-left: 0.5em;
}
.tag {
  font-size: 9px;
  letter-spacing: 0.4em;
  color: var(--ys-text-muted);
  font-weight: 500;
}
.studio-logo.inverse .tag { color: rgba(244, 239, 230, 0.65); }

.size-sm .chars { font-size: 18px; }
.size-sm .cloud-svg { width: 22px; height: 22px; }
.size-sm .tag { font-size: 7px; }

.size-md .chars { font-size: 26px; }
.size-md .cloud-svg { width: 30px; height: 30px; }

.size-lg .chars { font-size: 36px; letter-spacing: 0.4em; padding-left: 0.4em; }
.size-lg .cloud-svg { width: 38px; height: 38px; stroke-width: 1.2; }
.size-lg .tag { font-size: 11px; margin-top: 4px; }
</style>
