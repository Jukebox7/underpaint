import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxy /api vers le backend FastAPI (port 8000) en développement.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
