import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En producción Django sirve los archivos compilados bajo /static/ (WhiteNoise, ADR-08).
// En desarrollo, Vite reenvía /api al backend de Django conservando el encabezado Host
// (localhost:5173) para que coincida con ALLOWED_HOSTS y la verificación CSRF de Origin.
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/static/' : '/',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY ?? 'http://localhost:8000',
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/setupTests.js',
  },
}))
