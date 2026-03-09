import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.js'],
    coverage: {
      provider: 'v8',
      exclude: ['src/main.jsx', 'vite.config.js', 'eslint.config.js', 'tests/**'],
      thresholds: {
        lines: 70,
      },
    },
  },
})
