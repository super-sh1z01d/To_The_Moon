import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  base: '/app/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
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
      '/logs': 'http://localhost:8000',
    }
  }
})
