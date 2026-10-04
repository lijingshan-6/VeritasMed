import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  // GitHub Pages serves the replay build under /<repo>/; set VITE_BASE there.
  base: process.env.VITE_BASE ?? '/',
  plugins: [react(), tailwindcss()],
  server: {
    host: '127.0.0.1', // Local research demo only
    port: 5173,
    strictPort: true, // fail loudly if 5173 is taken (avoid silent jump to 5174)
    proxy: {
      // When VITE_API_URL is unset, /api and WS still work via same origin as the UI.
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
