/**
 * Auth Store (Pinia)
 *
 * Manages authentication state, user profile, and token lifecycle.
 * Tokens are stored in httpOnly cookies by the backend —
 * this store only tracks the in-memory user object and auth status.
 */

import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', () => {
  const { fetchApi } = useApi()

  // State
  const user = ref(null)
  const isLoading = ref(false)
  const error = ref(null)

  // Getters
  const isLoggedIn = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isOperator = computed(() => ['admin', 'operator', 'supervisor'].includes(user.value?.role))

  // Actions

  /**
   * Log in with username and password.
   */
  async function login(username, password) {
    isLoading.value = true
    error.value = null
    try {
      const data = await fetchApi('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      })
      if (data.data?.user) {
        user.value = data.data.user
      }
      return data
    } catch (err) {
      error.value = err.message || 'Login failed'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Fetch current user profile.
   */
  async function fetchUser() {
    isLoading.value = true
    error.value = null
    try {
      const data = await fetchApi('/api/auth/me')
      user.value = data
      return data
    } catch (err) {
      if (err.status === 401) {
        user.value = null
      } else {
        error.value = err.message || 'Failed to fetch user'
      }
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Log out and clear cookies.
   */
  async function logout() {
    isLoading.value = true
    try {
      await fetchApi('/api/auth/logout', { method: 'POST' })
    } catch (err) {
      // Ignore logout errors
    } finally {
      user.value = null
      isLoading.value = false
      error.value = null
    }
  }

  /**
   * Refresh access token using refresh cookie.
   */
  async function refreshToken() {
    try {
      await fetchApi('/api/auth/refresh', { method: 'POST' })
      return true
    } catch (err) {
      user.value = null
      return false
    }
  }

  /**
   * Initialize auth state on app startup.
   */
  async function initAuth() {
    try {
      await fetchUser()
    } catch (err) {
      // Access token may be expired — try refreshing
      if (err?.status === 401) {
        const refreshed = await refreshToken()
        if (refreshed) {
          try {
            await fetchUser()
            return
          } catch {
            // Refresh succeeded but user fetch failed — give up
          }
        }
      }
      user.value = null
    }
  }

  return {
    user,
    isLoading,
    error,
    isLoggedIn,
    isAdmin,
    isOperator,
    login,
    fetchUser,
    logout,
    refreshToken,
    initAuth,
  }
})
