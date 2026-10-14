import { defineConfig } from 'vite';

export default defineConfig({
  base: './',
  server: { port: 5178, host: '127.0.0.1', hmr: { overlay: false } },
  preview: { port: 5179, host: '127.0.0.1' },
  build: { target: 'es2022', chunkSizeWarningLimit: 2000 },
});
