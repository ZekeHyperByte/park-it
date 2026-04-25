import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('#app', () => ({
  useRuntimeConfig: () => ({
    public: { apiBaseUrl: 'http://localhost:8000' },
  }),
}))

vi.mock('../../composables/useApi.js', () => ({
  useApi: () => ({
    fetchApi: vi.fn(),
  }),
}))

describe('Website Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should have initial empty state', async () => {
    const { useWebsiteStore } = await import('../../stores/website.js')
    const store = useWebsiteStore()

    expect(store.gateIns).toEqual([])
    expect(store.gateOuts).toEqual([])
    expect(store.settings).toEqual([])
    expect(store.isLoading).toBe(false)
  })

  it('should filter active gate ins', async () => {
    const { useWebsiteStore } = await import('../../stores/website.js')
    const store = useWebsiteStore()
    store.gateIns = [
      { id: 1, name: 'Gate 1', is_active: true },
      { id: 2, name: 'Gate 2', is_active: false },
    ]

    expect(store.activeGateIns).toHaveLength(1)
    expect(store.activeGateIns[0].id).toBe(1)
  })

  it('should get setting by key with default', async () => {
    const { useWebsiteStore } = await import('../../stores/website.js')
    const store = useWebsiteStore()
    store.settings = [
      { key: 'app_name', value: 'E-Parking' },
    ]

    expect(store.getSetting('app_name')).toBe('E-Parking')
    expect(store.getSetting('missing_key', 'default')).toBe('default')
  })
})
