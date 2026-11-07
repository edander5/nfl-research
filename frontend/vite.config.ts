import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig({
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  plugins: [react(), tailwindcss()],
  server: { host: '127.0.0.1', port: 5173, strictPort: true, proxy: { '/api': { target: process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:8000', changeOrigin: true } } },
  test: { environment: 'jsdom', globals: true, setupFiles: ['./src/test/setup.ts'], restoreMocks: true },
});
