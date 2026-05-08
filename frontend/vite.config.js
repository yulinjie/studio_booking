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
    target: 'es2018', // 兼容老 Android WebView
    sourcemap: false, // 生产不暴露源码
    chunkSizeWarningLimit: 1500,
    cssCodeSplit: true,
    reportCompressedSize: false, // 加快构建
    rollupOptions: {
      output: {
        // hash 资源 + 静态资源分目录，方便 CDN/Caddy 长缓存
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: (info) => {
          const name = info.name || ''
          if (/\.(png|jpe?g|gif|svg|webp|ico)$/i.test(name)) return 'assets/img/[name]-[hash][extname]'
          if (/\.(woff2?|eot|ttf|otf)$/i.test(name)) return 'assets/font/[name]-[hash][extname]'
          if (/\.css$/i.test(name)) return 'assets/css/[name]-[hash][extname]'
          return 'assets/[name]-[hash][extname]'
        },
        manualChunks(id) {
          if (id.includes('node_modules')) {
            // echarts 仅 admin 用，单独 chunk 让 H5 用户不下载
            if (id.includes('echarts') || id.includes('zrender')) return 'vendor-echarts'
            if (id.includes('element-plus')) return 'vendor-element'
            if (id.includes('vant')) return 'vendor-vant'
            if (id.includes('lucide')) return 'vendor-lucide'
            if (id.includes('vue') || id.includes('pinia') || id.includes('@vue/')) return 'vendor-vue'
            // axios + dayjs 这类小工具集中
            if (id.includes('axios') || id.includes('dayjs')) return 'vendor-utils'
            return 'vendor'
          }
          // 业务代码按 layout 分组：少 chunk = 少 HTTP 请求
          if (id.includes('/pages/admin/')) return 'app-admin'
          if (id.includes('/pages/m/')) return 'app-mobile'
        },
      },
    },
  },
})
