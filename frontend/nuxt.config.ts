import { defineNuxtConfig } from 'nuxt/config'

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
    },
  },

  // CSS
  css: ['~/assets/css/main.css'],

  // Modules
  modules: [
    '@pinia/nuxt',
    '@element-plus/nuxt',
  ],

  // Pinia
  pinia: {
    storesDirs: ['./stores/**'],
  },

  // Element Plus
  elementPlus: {
    importStyle: 'css',
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
    },
  },
})
