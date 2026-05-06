import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const rawBasePath = env.VITE_BASE_PATH || ''
  const basePath = rawBasePath.replace(/\/+$|^\s+|\s+$/g, '')

  return {
    base: basePath ? `${basePath}/` : '/',
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': 'http://127.0.0.1:8000',
        '/health': 'http://127.0.0.1:8000'
      }
    }
  }
})
