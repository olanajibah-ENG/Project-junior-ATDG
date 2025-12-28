import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api/upm': {
        target: 'http://localhost:8000', // عنوان Django backend
        changeOrigin: true,
        secure: false,
      },
    },
  },
})