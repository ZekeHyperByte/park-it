import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

describe('Auth Store', () => {
  let fetchApiMock

  beforeEach(() => {
    setActivePinia(createPinia())
    fetchApiMock = vi.fn()
    globalThis.useApi = vi.fn(() => ({ fetchApi: fetchApiMock }))
  })

  it('should have initial state', async () => {
    const { useAuthStore } = await import('../../stores/auth.js')
    const store = useAuthStore()

    expect(store.user).toBeNull()
    expect(store.isLoading).toBe(false)
    expect(store.error).toBeNull()
    expect(store.isLoggedIn).toBe(false)
    expect(store.isAdmin).toBe(false)
  })

  it('should set user on login success', async () => {
    fetchApiMock.mockResolvedValue({
      message: 'Login successful',
      data: { user: { id: 1, username: 'admin', role: 'admin' } },
    })

    const { useAuthStore } = await import('../../stores/auth.js')
    const store = useAuthStore()

    await store.login('admin', 'admin123')

    expect(store.user).toEqual({ id: 1, username: 'admin', role: 'admin' })
    expect(store.isLoggedIn).toBe(true)
    expect(store.isAdmin).toBe(true)
  })

  it('should set error on login failure', async () => {
    fetchApiMock.mockRejectedValue(new Error('Invalid credentials'))

    const { useAuthStore } = await import('../../stores/auth.js')
    const store = useAuthStore()

    await expect(store.login('admin', 'wrong')).rejects.toThrow()
    expect(store.error).toBe('Invalid credentials')
  })

  it('should clear user on logout', async () => {
    fetchApiMock.mockResolvedValue({ message: 'Logout successful' })

    const { useAuthStore } = await import('../../stores/auth.js')
    const store = useAuthStore()
    store.user = { id: 1, username: 'admin', role: 'admin' }

    await store.logout()

    expect(store.user).toBeNull()
    expect(store.isLoggedIn).toBe(false)
  })
})
