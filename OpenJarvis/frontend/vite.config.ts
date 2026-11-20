import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  // Lee la URL del backend desde .env; si no existe usa localhost:8000.
  const zenitApiUrl = (env.VITE_ZENIT_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

  return {
    resolve: {
      alias: {
        '@': path.resolve(import.meta.dirname, './src'),
      },
    },
    plugins: [
      react(),
      tailwindcss(),
      VitePWA({
        registerType: 'autoUpdate',
        manifest: {
          name: 'ZENIT | La Esperanza',
          short_name: 'ZENIT',
          description: 'Alertas locales de desabasto para La Esperanza',
          theme_color: '#161618',
          background_color: '#161618',
          display: 'standalone',
          icons: [
            { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
            { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          ],
        },
        workbox: {
          globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
          navigateFallbackDenylist: [/^\/v1\//, /^\/health/, /^\/dashboard/, /^\/api\//],
        },
      }),
    ],
    build: {
      outDir: '../src/openjarvis/server/static',
      emptyOutDir: true,
      // Preserve the Vite 6 browser baseline for existing desktop webviews.
      target: ['es2020', 'edge88', 'firefox78', 'chrome87', 'safari14'],
      rolldownOptions: {
        output: {
          codeSplitting: {
            groups: [
              { name: 'react', test: /node_modules[\\/](react|react-dom)[\\/]/ },
              {
                name: 'markdown',
                test: /node_modules[\\/](react-markdown|rehype-highlight|remark-gfm)[\\/]/,
              },
              { name: 'charts', test: /node_modules[\\/]recharts[\\/]/ },
              { name: 'router', test: /node_modules[\\/]react-router[\\/]/ },
            ],
          },
        },
      },
    },
    server: {
      host: 'localhost',
      port: 5173,
      open: '/zenit',
      proxy: {
        // En dev el proxy redirige /api/zenit al backend usando la misma URL configurada.
        '/api/zenit': zenitApiUrl,
      },
    },
  };
});
