import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

const backendPaths = [
  '/admin',
  '/api',
  '/booking-confirmation',
  '/contact-submit',
  '/dashboard',
  '/images',
  '/login',
  '/logout',
  '/logo.svg',
  '/payment-cancel',
  '/payment-success',
  '/pictures',
  '/properties',
  '/register',
  '/review-submit',
  '/reviews',
  '/stripe-webhook',
  '/vendor',
];

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: Object.fromEntries(backendPaths.map((path) => [path, 'http://127.0.0.1:5000'])),
  },
});
