import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/app/',
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/health': 'http://localhost:8000',
      '/version': 'http://localhost:8000',
      '/settings': 'http://localhost:8000',
      '/tokens': 'http://localhost:8000',
      '/admin': 'http://localhost:8000',
    }
  }
})
