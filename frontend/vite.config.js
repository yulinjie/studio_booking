import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { VantResolver } from '@vant/auto-import-resolver'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      imports: ['vue', 'vue-router', 'pinia'],
      resolvers: [ElementPlusResolver()],
      dts: false,
    }),
    Components({
      resolvers: [ElementPlusResolver(), VantResolver()],
      dts: false,
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  build: {
    outDir: '../backend/static',
    emptyOutDir: true,
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        // 把第三方大库拆成单独 chunk —— 浏览器只在用到时下载，且强缓存命中率高
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('echarts')) return 'vendor-echarts'
            if (id.includes('element-plus')) return 'vendor-element'
            if (id.includes('vant')) return 'vendor-vant'
            if (id.includes('lucide')) return 'vendor-lucide'
            if (id.includes('vue') || id.includes('pinia')) return 'vendor-vue'
            return 'vendor'
          }
        },
      },
    },
  },
})
