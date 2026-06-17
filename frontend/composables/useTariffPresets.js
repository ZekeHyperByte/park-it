/**
 * Tariff preset bundles for the setup wizard.
 *
 * Each preset is a starting point — the technician edits the resulting
 * vehicle types and prices inline before saving.
 *
 * `rate_type` values match the backend VehicleType model:
 *   "flat"        — single flat fee, regardless of duration
 *   "hourly"      — first_hour_rate, then per_hour_rate
 *   "progressive" — first_hour_rate, escalating per_hour_rate
 *
 * Amounts are in IDR (no decimals).
 */

export function useTariffPresets() {
  const presets = [
    {
      id: 'indonesian_mall',
      name: 'Mall Indonesia',
      description: 'Tarif khas pusat perbelanjaan: jam pertama lebih mahal, lalu murah per jam berikutnya.',
      items: [
        {
          name: 'Motor',
          rate_type: 'hourly',
          first_hour_rate: 2000,
          per_hour_rate: 1000,
          daily_cap: 15000,
        },
        {
          name: 'Mobil',
          rate_type: 'hourly',
          first_hour_rate: 5000,
          per_hour_rate: 2000,
          daily_cap: 30000,
        },
        {
          name: 'Truk',
          rate_type: 'hourly',
          first_hour_rate: 10000,
          per_hour_rate: 3000,
          daily_cap: 60000,
        },
      ],
    },
    {
      id: 'office_building',
      name: 'Gedung Perkantoran',
      description: 'Tarif flat untuk motor, berjenjang untuk mobil sesuai durasi.',
      items: [
        {
          name: 'Motor',
          rate_type: 'flat',
          first_hour_rate: 3000,
          per_hour_rate: 0,
          daily_cap: 3000,
        },
        {
          name: 'Mobil',
          rate_type: 'progressive',
          first_hour_rate: 5000,
          per_hour_rate: 3000,
          daily_cap: 50000,
        },
      ],
    },
    {
      id: 'apartment',
      name: 'Apartemen / Komplek',
      description: 'Member-friendly, tarif tamu sederhana.',
      items: [
        {
          name: 'Motor',
          rate_type: 'flat',
          first_hour_rate: 2000,
          per_hour_rate: 0,
          daily_cap: 2000,
        },
        {
          name: 'Mobil',
          rate_type: 'flat',
          first_hour_rate: 5000,
          per_hour_rate: 0,
          daily_cap: 5000,
        },
      ],
    },
    {
      id: 'hospital',
      name: 'Rumah Sakit',
      description: 'Tarif rendah jam pertama, naik moderat, cap harian terjangkau.',
      items: [
        {
          name: 'Motor',
          rate_type: 'hourly',
          first_hour_rate: 1000,
          per_hour_rate: 500,
          daily_cap: 8000,
        },
        {
          name: 'Mobil',
          rate_type: 'hourly',
          first_hour_rate: 3000,
          per_hour_rate: 2000,
          daily_cap: 20000,
        },
      ],
    },
  ]

  function findPreset(id) {
    return presets.find((p) => p.id === id) || null
  }

  function clonePreset(id) {
    const preset = findPreset(id)
    if (!preset) return null
    return {
      ...preset,
      items: preset.items.map((item) => ({ ...item })),
    }
  }

  return {
    presets,
    findPreset,
    clonePreset,
  }
}
