<script setup>
/*
  H5 列表骨架屏：基于 Vant Skeleton 封装，统一样式。
  用在首屏加载（替代"加载中..."）和下拉刷新时的占位。
*/
defineProps({
  count: { type: Number, default: 3 }, // 渲染几张占位卡
  // 'card' = 卡片布局；'row' = 单行布局（无图）
  variant: { type: String, default: 'card' },
})
</script>

<template>
  <div class="skel-wrap">
    <div v-for="i in count" :key="i" class="skel-card" :class="`skel-${variant}`">
      <van-skeleton :row="variant === 'card' ? 3 : 2" row-width="80%" :avatar="variant === 'card'" avatar-shape="square" :loading="true" title />
    </div>
  </div>
</template>

<style scoped>
.skel-wrap {
  padding: 12px;
}
.skel-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.skel-card :deep(.van-skeleton__avatar--square) {
  border-radius: 8px;
  width: 64px;
  height: 64px;
}
</style>
