import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'
// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    uni(),
  ],
  server: {
    port: 5177,
    strictPort: true,
    host: true,
    proxy: {
      // H5 开发用相对路径 /api 时转发到本机后端，避免内嵌预览/局域网打开页面时 127.0.0.1 指向错误机器导致 404 Not Found
      '/api': {
        // 若本机 8000 被旧进程占满无法释放，后端可改用: python -m uvicorn app.main:app --reload --port 8001
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
})
