import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The backend (backend/app/main.py) has no CORS middleware configured, and
// per this task's instructions the backend must not be modified. Rather
// than add CORS server-side, the dev server proxies /api/* to the real
// backend so browser requests are same-origin. See src/api/client.ts.
const BACKEND_ORIGIN = process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: BACKEND_ORIGIN,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
