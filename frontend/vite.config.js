import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: { outDir: 'dist', sourcemap: false },
  server: {
    // Local dev only; in production nginx proxies /api to uvicorn.
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
