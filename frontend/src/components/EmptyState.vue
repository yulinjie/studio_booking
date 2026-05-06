<script setup>
defineProps({
  illust: { type: String, default: 'lotus' },   // lotus | calendar | cards | bookmark | empty
  title: String,
  sub: String,
})
</script>

<template>
  <div class="empty-state">
    <svg v-if="illust === 'lotus'" viewBox="0 0 120 120" class="illust" xmlns="http://www.w3.org/2000/svg">
      <g stroke="currentColor" stroke-width="1.4" fill="none" opacity="0.55">
        <ellipse cx="60" cy="76" rx="36" ry="6" />
        <path d="M60 70 Q40 56 32 70 Q40 78 60 76 Z" fill="currentColor" fill-opacity="0.12" />
        <path d="M60 70 Q80 56 88 70 Q80 78 60 76 Z" fill="currentColor" fill-opacity="0.12" />
        <path d="M60 70 Q44 50 50 38 Q60 48 60 70 Z" fill="currentColor" fill-opacity="0.18" />
        <path d="M60 70 Q76 50 70 38 Q60 48 60 70 Z" fill="currentColor" fill-opacity="0.18" />
        <path d="M60 70 Q60 56 60 40" stroke-linecap="round" />
        <circle cx="60" cy="36" r="3" fill="currentColor" />
      </g>
    </svg>

    <svg v-else-if="illust === 'calendar'" viewBox="0 0 120 120" class="illust" xmlns="http://www.w3.org/2000/svg">
      <g stroke="currentColor" stroke-width="1.4" fill="none" opacity="0.55">
        <rect x="28" y="32" width="64" height="60" rx="8" />
        <line x1="28" y1="48" x2="92" y2="48" />
        <line x1="42" y1="24" x2="42" y2="40" stroke-linecap="round" />
        <line x1="78" y1="24" x2="78" y2="40" stroke-linecap="round" />
        <circle cx="46" cy="62" r="2" fill="currentColor" />
        <circle cx="60" cy="62" r="2" fill="currentColor" />
        <circle cx="74" cy="62" r="2" fill="currentColor" />
        <circle cx="46" cy="76" r="2" fill="currentColor" />
        <circle cx="60" cy="76" r="2" fill="currentColor" opacity="0.4" />
      </g>
    </svg>

    <svg v-else-if="illust === 'cards'" viewBox="0 0 120 120" class="illust" xmlns="http://www.w3.org/2000/svg">
      <g stroke="currentColor" stroke-width="1.4" fill="none" opacity="0.55">
        <rect x="22" y="44" width="60" height="40" rx="6" transform="rotate(-8 52 64)" />
        <rect x="38" y="36" width="60" height="40" rx="6" transform="rotate(6 68 56)" fill="currentColor" fill-opacity="0.06" />
        <line x1="48" y1="50" x2="78" y2="50" transform="rotate(6 68 56)" />
        <line x1="48" y1="58" x2="68" y2="58" transform="rotate(6 68 56)" />
      </g>
    </svg>

    <svg v-else-if="illust === 'bookmark'" viewBox="0 0 120 120" class="illust" xmlns="http://www.w3.org/2000/svg">
      <g stroke="currentColor" stroke-width="1.4" fill="none" opacity="0.55">
        <path d="M40 28 H80 V92 L60 78 L40 92 Z" fill="currentColor" fill-opacity="0.08" />
        <path d="M50 50 L58 58 L72 44" stroke-linecap="round" stroke-linejoin="round" />
      </g>
    </svg>

    <svg v-else viewBox="0 0 120 120" class="illust" xmlns="http://www.w3.org/2000/svg">
      <circle cx="60" cy="60" r="40" stroke="currentColor" stroke-width="1.4" fill="none" opacity="0.4" />
    </svg>

    <div v-if="title" class="title">{{ title }}</div>
    <div v-if="sub" class="sub">{{ sub }}</div>
    <slot />
  </div>
</template>

<style scoped>
.empty-state {
  text-align: center;
  padding: 48px 20px;
  color: var(--ys-text-muted);
}
.illust {
  width: 100px; height: 100px;
  color: var(--ys-primary);
}
.title { font-size: 14px; margin-top: 12px; letter-spacing: 1px; color: var(--ys-text-soft); }
.sub { font-size: 12px; margin-top: 4px; color: var(--ys-text-light); }
</style>
