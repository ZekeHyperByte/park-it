import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  devtools: { enabled: true },

  // Compatibility
  compatibilityDate: '2025-04-25',

  // Runtime config
  // NOTE: In production, set NUXT_PUBLIC_API_BASE_URL="" for relative URLs
  // through nginx. The default below is for development only.
  runtimeConfig: {
    public: {
      apiBaseUrl: process.env.NUXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
      wsBaseUrl: process.env.NUXT_PUBLIC_WS_BASE_URL || 'ws://localhost:8000',
      boothBridgeUrl: process.env.NUXT_PUBLIC_BOOTH_BRIDGE_URL || 'ws://localhost:5678/',
    },
  },

  // CSS — Tailwind v4
  css: [
    '~/assets/css/tailwind.css',
  ],

  // Modules
  modules: [
    '@pinia/nuxt',
    'shadcn-nuxt',
  ],

  // Pinia
  pinia: {
    storesDirs: ['./stores/**'],
  },

  // shadcn-vue
  shadcn: {
    prefix: '',
    componentDir: './components/ui',
  },

  // Vite — Tailwind v4 plugin
  vite: {
    plugins: [
      tailwindcss(),
    ],
  },

  // Nitro / server
  nitro: {
    preset: 'node-server',
  },

  // App
  app: {
    head: {
      title: 'E-Parking v2',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      ],
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Caveat:wght@500;600;700&family=Patrick+Hand&family=Kalam:wght@400;700&display=swap' },
      ],
    },
  },
})
