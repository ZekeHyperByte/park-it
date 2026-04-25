/**
 * Auth Middleware
 *
 * Protects routes that require authentication.
 * Redirects unauthenticated users to /login.
 * Redirects authenticated users away from /login.
 */

export default defineNuxtRouteMiddleware(async (to, from) => {
  const authStore = useAuthStore()

  // Initialize auth if not yet loaded
  if (!authStore.user && !authStore.isLoading) {
    try {
      await authStore.fetchUser()
    } catch {
      // Not authenticated
    }
  }

  const publicRoutes = ['/login']

  // If not logged in and trying to access a protected route
  if (!authStore.isLoggedIn && !publicRoutes.includes(to.path)) {
    return navigateTo('/login')
  }

  // If logged in and trying to access login page
  if (authStore.isLoggedIn && to.path === '/login') {
    return navigateTo('/')
  }
})
