/**
 * Mounts a global vue-sonner <Toaster /> so any component (or composable)
 * can call `toast.success(...)` / `toast.error(...)`.
 *
 * Without this plugin, vue-sonner's exported `toast` API is a no-op because
 * there's no Toaster instance subscribing to its event bus.
 */
import { defineNuxtPlugin } from 'nuxt/app'
import { Toaster, toast } from 'vue-sonner'

export default defineNuxtPlugin((nuxtApp) => {
  // Render the Toaster at the app root so toasts persist across route changes.
  nuxtApp.vueApp.component('Toaster', Toaster)

  // Expose imperatively for legacy callers that do useNuxtApp().$toast.success(...)
  return {
    provide: {
      toast,
    },
  }
})
