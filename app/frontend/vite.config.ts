import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const apiTarget = process.env.VITE_DEV_API_PROXY ?? 'http://localhost:5001';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setupTests.ts'],
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/upload': apiTarget,
      '/share': apiTarget,
      '/files': apiTarget,
      '/qrcode': apiTarget,
      '/health': apiTarget,
    },
  },
});
