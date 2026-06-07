import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const TARGET = 'https://adel-intelligence.com'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': { target: TARGET, changeOrigin: true, secure: true },
      '/oauth/register': { target: TARGET, changeOrigin: true, secure: true },
      '/oauth/token': { target: TARGET, changeOrigin: true, secure: true },
      '/oauth/authorize': { target: TARGET, changeOrigin: true, secure: true },
      '/.well-known': { target: TARGET, changeOrigin: true, secure: true },
      '/banking/analyse': { target: TARGET, changeOrigin: true, secure: true },
      '/jobs':            { target: TARGET, changeOrigin: true, secure: true },
    },
  },
})
