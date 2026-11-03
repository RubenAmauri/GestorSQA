import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En producción Django sirve los archivos compilados bajo /static/ (WhiteNoise, ADR-08).
// En desarrollo, Vite reenvía /api al backend de Django.
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/static/' : '/',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/setupTests.js',
  },
}))
