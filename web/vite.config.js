import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const appBasePath = process.env.VITE_APP_BASE_PATH || '/contratos/'

export default defineConfig({
  base: appBasePath,
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000'
    }
  }
})
