/**
 * Vitest setup file
 *
 * Provides global mocks for Nuxt 3 auto-imports so unit tests
 * work without running the full Nuxt dev server.
 */

import { vi } from 'vitest'
import { ref, computed, reactive, watch } from 'vue'

// Make Vue reactivity APIs globally available (matches Nuxt auto-imports)
globalThis.ref = ref
globalThis.computed = computed
globalThis.reactive = reactive
globalThis.watch = watch

// Mock Nuxt app composables
globalThis.useRuntimeConfig = vi.fn(() => ({
  public: {
    apiBaseUrl: 'http://localhost:8000',
    wsBaseUrl: 'ws://localhost:8000',
  },
}))

globalThis.useNuxtApp = vi.fn(() => ({
  $ws: {
    connect: vi.fn(),
    disconnect: vi.fn(),
    on: vi.fn(() => vi.fn()),
    send: vi.fn(() => true),
    isConnected: vi.fn(() => false),
    disconnectAll: vi.fn(),
  },
  provide: {},
}))

globalThis.useRoute = vi.fn(() => ({ path: '/' }))
globalThis.useRouter = vi.fn(() => ({
  push: vi.fn(),
  replace: vi.fn(),
}))

globalThis.navigateTo = vi.fn()

globalThis.defineNuxtRouteMiddleware = vi.fn((fn) => fn)
globalThis.defineNuxtPlugin = vi.fn((fn) => fn)

// Mock Element Plus message
//globalThis.ElMessage = vi.fn()
//globalThis.ElMessageBox = vi.fn()
//globalThis.ElNotification = vi.fn()

// Mock useApi globally for store tests
const mockFetchApi = vi.fn()
globalThis.useApi = vi.fn(() => ({
  fetchApi: mockFetchApi,
  baseURL: 'http://localhost:8000',
}))
