import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

vi.mock('#app', () => ({
  useRuntimeConfig: () => ({
    public: { apiBaseUrl: 'http://localhost:8000' },
  }),
}))

describe('useCrud', () => {
  let fetchApiMock

  beforeEach(() => {
    fetchApiMock = vi.fn()
    globalThis.useApi = vi.fn(() => ({ fetchApi: fetchApiMock }))
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should throw if resourcePath is missing', () => {
    const { useCrud } = require('../../composables/useCrud.js')
    expect(() => useCrud()).toThrow('useCrud requires a resourcePath')
  })

  it('should perform GET list', async () => {
    fetchApiMock.mockResolvedValue([{ id: 1 }, { id: 2 }])

    const { useCrud } = await import('../../composables/useCrud.js')
    const crud = useCrud('/api/users')
    const result = await crud.list()

    expect(fetchApiMock).toHaveBeenCalledWith('/api/users')
    expect(result).toEqual([{ id: 1 }, { id: 2 }])
  })

  it('should perform GET list with query params', async () => {
    fetchApiMock.mockResolvedValue([])

    const { useCrud } = await import('../../composables/useCrud.js')
    const crud = useCrud('/api/users')
    await crud.list({ page: 1, role: 'admin' })

    expect(fetchApiMock).toHaveBeenCalledWith('/api/users?page=1&role=admin')
  })

  it('should perform GET by id', async () => {
    fetchApiMock.mockResolvedValue({ id: 1, username: 'admin' })

    const { useCrud } = await import('../../composables/useCrud.js')
    const crud = useCrud('/api/users')
    const result = await crud.get(1)

    expect(fetchApiMock).toHaveBeenCalledWith('/api/users/1')
    expect(result.username).toBe('admin')
  })

  it('should perform POST create', async () => {
    fetchApiMock.mockResolvedValue({ id: 3 })

    const { useCrud } = await import('../../composables/useCrud.js')
    const crud = useCrud('/api/users')
    const payload = { username: 'newuser', password: 'pass123' }
    await crud.create(payload)

    expect(fetchApiMock).toHaveBeenCalledWith('/api/users', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  })

  it('should perform PATCH update', async () => {
    fetchApiMock.mockResolvedValue({ id: 1, role: 'supervisor' })

    const { useCrud } = await import('../../composables/useCrud.js')
    const crud = useCrud('/api/users')
    await crud.update(1, { role: 'supervisor' })

    expect(fetchApiMock).toHaveBeenCalledWith('/api/users/1', {
      method: 'PATCH',
      body: JSON.stringify({ role: 'supervisor' }),
    })
  })

  it('should perform DELETE remove', async () => {
    fetchApiMock.mockResolvedValue({ message: 'deleted' })

    const { useCrud } = await import('../../composables/useCrud.js')
    const crud = useCrud('/api/users')
    await crud.remove(1)

    expect(fetchApiMock).toHaveBeenCalledWith('/api/users/1', {
      method: 'DELETE',
    })
  })
})
