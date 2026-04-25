import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Mock Nuxt runtime config
vi.mock('#app', () => ({
  useRuntimeConfig: () => ({
    public: {
      apiBaseUrl: 'http://localhost:8000',
    },
  }),
}))

// We need to import the composable after mocking
describe('useApi', () => {
  let fetchMock

  beforeEach(() => {
    fetchMock = vi.fn()
    global.fetch = fetchMock
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should construct correct URL with base', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      headers: new Map([['content-type', 'application/json']]),
      json: async () => ({ status: 'ok' }),
    })

    // Dynamic import to pick up the mock
    const { useApi } = await import('../../composables/useApi.js')
    const { fetchApi } = useApi()
    await fetchApi('/api/health')

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/health',
      expect.objectContaining({
        credentials: 'include',
        headers: expect.objectContaining({
          Accept: 'application/json',
          'Content-Type': 'application/json',
        }),
      })
    )
  })

  it('should send JSON body with correct headers', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      headers: new Map([['content-type', 'application/json']]),
      json: async () => ({ id: 1 }),
    })

    const { useApi } = await import('../../composables/useApi.js')
    const { fetchApi } = useApi()
    await fetchApi('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username: 'admin', password: 'secret' }),
    })

    const callArgs = fetchMock.mock.calls[0]
    expect(callArgs[1].method).toBe('POST')
    expect(callArgs[1].body).toBe(JSON.stringify({ username: 'admin', password: 'secret' }))
  })

  it('should strip Content-Type for FormData', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      headers: new Map(),
      json: async () => ({}),
    })

    const { useApi } = await import('../../composables/useApi.js')
    const { fetchApi } = useApi()
    const formData = new FormData()
    await fetchApi('/api/upload', {
      method: 'POST',
      body: formData,
    })

    const callArgs = fetchMock.mock.calls[0]
    expect(callArgs[1].headers['Content-Type']).toBeUndefined()
  })

  it('should throw on HTTP error with status and data', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 401,
      headers: new Map([['content-type', 'application/json']]),
      json: async () => ({ detail: 'Unauthorized' }),
    })

    const { useApi } = await import('../../composables/useApi.js')
    const { fetchApi } = useApi()

    await expect(fetchApi('/api/protected')).rejects.toThrow('Unauthorized')
    try {
      await fetchApi('/api/protected')
    } catch (err) {
      expect(err.status).toBe(401)
      expect(err.data).toEqual({ detail: 'Unauthorized' })
    }
  })

  it('should return parsed JSON on success', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      headers: new Map([['content-type', 'application/json']]),
      json: async () => ({ message: 'success', data: { id: 1 } }),
    })

    const { useApi } = await import('../../composables/useApi.js')
    const { fetchApi } = useApi()
    const result = await fetchApi('/api/health')

    expect(result).toEqual({ message: 'success', data: { id: 1 } })
  })
})
