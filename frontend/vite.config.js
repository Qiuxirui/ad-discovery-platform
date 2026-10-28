import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 同源部署：生产由 FastAPI 单端口托管 dist/，前端一律走相对路径 /api、/static。
// 开发期仅由 vite dev server 反向代理到本机后端，代理配置不进构建产物。
export default defineConfig({
  base: '/',
  plugins: [react()],
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    emptyOutDir: true,
    chunkSizeWarningLimit: 900,
  },
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
