import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default ({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const appBasePath = env.VITE_APP_BASE_PATH || '/'

  return defineConfig({
    base: appBasePath,
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      proxy: {
        '/api': 'http://127.0.0.1:8000',
        '/health': 'http://127.0.0.1:8000',
        '/ws': {
          target: 'ws://127.0.0.1:8000',
          ws: true,
        },
        '/contratos/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/contratos/, ''),
        },
        '/contratos/health': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/contratos/, ''),
        },
        '/contratos/ws': {
          target: 'ws://127.0.0.1:8000',
          ws: true,
          rewrite: (path) => path.replace(/^\/contratos/, ''),
        },
      },
    },
  })
}
