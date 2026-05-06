/**
 * Website Store (Pinia)
 *
 * Reference data cache: gates, vehicle types, tariffs, members, readers.
 * Loaded once at startup and refreshed on demand.
 */

import { defineStore } from 'pinia'

export const useWebsiteStore = defineStore('website', () => {
  const { fetchApi } = useApi()

  // State
  const gateIns = ref([])
  const gateOuts = ref([])
  const vehicleTypes = ref([])
  const settings = ref([])
  const isLoading = ref(false)
  const error = ref(null)

  // Getters
  const activeGateIns = computed(() => gateIns.value.filter((g) => g.is_active))
  const activeGateOuts = computed(() => gateOuts.value.filter((g) => g.is_active))

  // Actions

  async function fetchGateIns() {
    try {
      const data = await fetchApi('/api/gates?direction=IN')
      gateIns.value = data || []
    } catch (err) {
      error.value = err.message
    }
  }

  async function fetchGateOuts() {
    try {
      const data = await fetchApi('/api/gates?direction=OUT')
      gateOuts.value = data || []
    } catch (err) {
      error.value = err.message
    }
  }

  async function fetchVehicleTypes() {
    try {
      const data = await fetchApi('/api/vehicle-types')
      vehicleTypes.value = data || []
    } catch (err) {
      error.value = err.message
    }
  }

  async function fetchSettings() {
    try {
      const data = await fetchApi('/api/settings')
      settings.value = data || []
    } catch (err) {
      error.value = err.message
    }
  }

  /**
   * Load all reference data in parallel.
   */
  async function loadAll() {
    isLoading.value = true
    error.value = null
    try {
      await Promise.all([
        fetchGateIns(),
        fetchGateOuts(),
        fetchVehicleTypes(),
        fetchSettings(),
      ])
    } catch (err) {
      error.value = err.message
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Get a setting value by key.
   */
  function getSetting(key, defaultValue = null) {
    const s = settings.value.find((item) => item.key === key)
    return s ? s.value : defaultValue
  }

  return {
    gateIns,
    gateOuts,
    vehicleTypes,
    settings,
    isLoading,
    error,
    activeGateIns,
    activeGateOuts,
    fetchGateIns,
    fetchGateOuts,
    fetchVehicleTypes,
    fetchSettings,
    loadAll,
    getSetting,
  }
})
