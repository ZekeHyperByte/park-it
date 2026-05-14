<template>
  <SetupShell
    :steps="steps"
    :current-index="currentIndex"
    :can-advance="canAdvance"
    :busy="busy"
    :autosaved-label="autosavedLabel"
    :final-step="isFinalStep"
    @next="onNext"
    @back="onBack"
    @navigate="onNavigate"
    @finalize="onFinalize"
    @help="showHelp = !showHelp"
  >
    <!-- Step: Welcome / Token redeem -->
    <section v-if="step === 'welcome'" class="space-y-6">
      <header class="space-y-2">
        <h2 class="text-2xl font-bold text-foreground">Selamat datang</h2>
        <p class="text-sm text-muted-foreground">
          Ayo siapkan E-Parking. Sekitar 20 menit. Anda butuh: IP controller, jaringan booth PC, dan perangkat keras menyala.
        </p>
      </header>

      <TokenGate
        v-if="!sessionActive"
        :loading="tokenLoading"
        :error="tokenError"
        @submit="redeemManualToken"
      />

      <div v-else class="space-y-4">
        <div class="rounded-lg border border-success/30 bg-success/10 p-4 text-sm text-success">
          ✓ Token setup tervalidasi. Sesi setup aktif.
        </div>

        <section class="space-y-3">
          <div class="flex items-center justify-between gap-2">
            <h3 class="text-sm font-semibold text-foreground">Pemeriksaan awal</h3>
            <Button variant="outline" size="sm" :disabled="preflightLoading" @click="runPreflight">
              {{ preflightLoading ? 'Memeriksa…' : 'Jalankan' }}
            </Button>
          </div>
          <PreflightList :checks="preflight.checks" />
          <p v-if="preflight.failed > 0" class="text-xs text-destructive">
            Ada {{ preflight.failed }} pemeriksaan gagal. Perbaiki sebelum lanjut.
          </p>
        </section>
      </div>
    </section>

    <!-- Step: Create admin -->
    <section v-else-if="step === 'admin'" class="space-y-5">
      <header class="space-y-1">
        <h2 class="text-xl font-bold text-foreground">Buat akun administrator</h2>
        <p class="text-sm text-muted-foreground">
          Akun pertama. Anda bisa menambah operator lain dari menu setelah wizard selesai.
        </p>
      </header>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <WizardField label="Username" required helper="Tanpa spasi. Contoh: admin">
          <Input v-model="form.admin.username" autocomplete="username" />
        </WizardField>
        <WizardField label="Nama lengkap" required>
          <Input v-model="form.admin.full_name" autocomplete="name" />
        </WizardField>
        <WizardField label="Email" required>
          <Input v-model="form.admin.email" type="email" autocomplete="email" />
        </WizardField>
        <div class="hidden sm:block" />
        <WizardField label="Password" required helper="Min. 8 karakter">
          <Input v-model="form.admin.password" type="password" autocomplete="new-password" />
        </WizardField>
        <WizardField
          label="Konfirmasi password"
          required
          :error="form.admin.password && form.admin.confirm && form.admin.password !== form.admin.confirm ? 'Password tidak cocok.' : ''"
        >
          <Input v-model="form.admin.confirm" type="password" autocomplete="new-password" />
        </WizardField>
      </div>

      <div v-if="errors.admin" class="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
        {{ errors.admin }}
      </div>
    </section>

    <!-- Step: Site info -->
    <section v-else-if="step === 'site'" class="space-y-5">
      <header class="space-y-1">
        <h2 class="text-xl font-bold text-foreground">Informasi lokasi</h2>
        <p class="text-sm text-muted-foreground">Muncul di struk dan laporan.</p>
      </header>

      <div class="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_320px]">
        <div class="space-y-4">
          <WizardField label="Nama lokasi" required>
            <Input v-model="form.site.name" placeholder="Parkir Mall ABC" />
          </WizardField>
          <WizardField label="Alamat">
            <Input v-model="form.site.address" placeholder="Jl. Sudirman No. 1" />
          </WizardField>
          <div class="grid grid-cols-2 gap-3">
            <WizardField label="Kota">
              <Input v-model="form.site.city" />
            </WizardField>
            <WizardField label="Telepon">
              <Input v-model="form.site.phone" placeholder="021-xxxx" />
            </WizardField>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <WizardField label="Email">
              <Input v-model="form.site.email" type="email" />
            </WizardField>
            <WizardField label="NPWP / Tax ID">
              <Input v-model="form.site.tax_id" />
            </WizardField>
          </div>
        </div>

        <aside class="rounded-lg border border-border bg-background p-4 font-mono text-xs text-foreground">
          <p class="mb-2 text-center text-muted-foreground">— Pratinjau Struk —</p>
          <p class="text-center text-base font-bold">{{ form.site.name || 'Parkir Anda' }}</p>
          <p v-if="form.site.address" class="text-center">{{ form.site.address }}</p>
          <p v-if="form.site.city" class="text-center">{{ form.site.city }}</p>
          <p v-if="form.site.phone" class="text-center">Telp. {{ form.site.phone }}</p>
          <p v-if="form.site.tax_id" class="text-center">NPWP {{ form.site.tax_id }}</p>
          <p class="my-2 border-t border-dashed border-border" />
          <p>Tiket #000001</p>
          <p>Motor — {{ today }}</p>
          <p>Rp 2.000</p>
        </aside>
      </div>
    </section>

    <!-- Step: Tariff (presets + table) -->
    <section v-else-if="step === 'tariff'" class="space-y-5">
      <header class="space-y-1">
        <h2 class="text-xl font-bold text-foreground">Jenis kendaraan & tarif</h2>
        <p class="text-sm text-muted-foreground">
          Pilih preset terdekat, lalu sesuaikan harga di tabel di bawah.
        </p>
      </header>

      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <TariffPresetCard
          v-for="preset in tariffPresets.presets"
          :key="preset.id"
          :preset="preset"
          :selected="form.tariff.preset === preset.id"
          @apply="applyPreset"
        />
      </div>

      <div class="rounded-lg border border-border bg-background overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-surface-hover text-xs uppercase text-muted-foreground">
            <tr>
              <th class="px-3 py-2 text-left">Nama</th>
              <th class="px-3 py-2 text-left">Kode</th>
              <th class="px-3 py-2 text-right">Tarif jam-1</th>
              <th class="px-3 py-2 text-right">Per jam</th>
              <th class="px-3 py-2 text-right">Cap harian</th>
              <th class="px-3 py-2 text-center">Progresif</th>
              <th class="px-3 py-2" />
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <tr v-for="(item, idx) in form.tariff.items" :key="idx">
              <td class="px-3 py-2"><Input v-model="item.name" class="h-8" /></td>
              <td class="px-3 py-2"><Input v-model="item.code" class="h-8 font-mono" /></td>
              <td class="px-3 py-2"><Input v-model.number="item.base_tariff" type="number" min="0" class="h-8 text-right" /></td>
              <td class="px-3 py-2"><Input v-model.number="item.hourly_rate" type="number" min="0" class="h-8 text-right" /></td>
              <td class="px-3 py-2"><Input v-model.number="item.max_daily_cap" type="number" min="0" class="h-8 text-right" /></td>
              <td class="px-3 py-2 text-center">
                <input type="checkbox" v-model="item.is_progressive" class="h-4 w-4 accent-primary" />
              </td>
              <td class="px-3 py-2 text-right">
                <Button variant="ghost" size="sm" @click="removeTariffItem(idx)">Hapus</Button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="flex justify-between">
        <Button variant="outline" @click="addTariffItem">+ Tambah jenis</Button>
        <p v-if="errors.tariff" class="text-xs text-destructive">{{ errors.tariff }}</p>
      </div>
    </section>

    <!-- Step: Areas -->
    <section v-else-if="step === 'areas'" class="space-y-5">
      <header class="space-y-1">
        <h2 class="text-xl font-bold text-foreground">Area parkir & kapasitas</h2>
        <p class="text-sm text-muted-foreground">
          Setidaknya satu area. Tambah lagi nanti kalau perlu.
        </p>
      </header>

      <div class="rounded-lg border border-border bg-background overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-surface-hover text-xs uppercase text-muted-foreground">
            <tr>
              <th class="px-3 py-2 text-left">Nama area</th>
              <th class="px-3 py-2 text-left">Kode</th>
              <th class="px-3 py-2 text-right">Kapasitas</th>
              <th class="px-3 py-2" />
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <tr v-for="(area, idx) in form.areas" :key="idx">
              <td class="px-3 py-2"><Input v-model="area.name" class="h-8" placeholder="Area Utama" /></td>
              <td class="px-3 py-2"><Input v-model="area.code" class="h-8 font-mono" placeholder="MAIN" /></td>
              <td class="px-3 py-2"><Input v-model.number="area.capacity" type="number" min="0" class="h-8 text-right" /></td>
              <td class="px-3 py-2 text-right">
                <Button variant="ghost" size="sm" :disabled="form.areas.length <= 1" @click="removeArea(idx)">Hapus</Button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <Button variant="outline" @click="addArea">+ Tambah area</Button>
      <p v-if="errors.areas" class="text-sm text-destructive">{{ errors.areas }}</p>
    </section>

    <!-- Step: Topology, gates, booth, go-live — placeholders for P2/P3 -->
    <section v-else-if="step === 'topology'" class="space-y-4">
      <header class="space-y-1">
        <h2 class="text-xl font-bold text-foreground">Topologi sistem</h2>
        <p class="text-sm text-muted-foreground">
          Akan diisi di tahap berikutnya (deteksi otomatis + pemilihan).
        </p>
      </header>
      <div class="rounded-lg border border-border bg-background p-6 text-sm text-muted-foreground">
        <p>Topologi terdeteksi: <span class="font-mono text-foreground">{{ state.topology }}</span></p>
      </div>
    </section>

    <section v-else-if="step === 'gates'" class="space-y-4">
      <header class="space-y-1">
        <h2 class="text-xl font-bold text-foreground">Perangkat per gate</h2>
        <p class="text-sm text-muted-foreground">
          Akan diisi di tahap deteksi serial (P2).
        </p>
      </header>
    </section>

    <section v-else-if="step === 'booth'" class="space-y-4">
      <header class="space-y-1">
        <h2 class="text-xl font-bold text-foreground">Loket / Booth PC</h2>
        <p class="text-sm text-muted-foreground">Akan diisi setelah konfigurasi gate.</p>
      </header>
    </section>

    <section v-else-if="step === 'finalize'" class="space-y-4">
      <header class="space-y-1">
        <h2 class="text-xl font-bold text-foreground">Siap aktifkan</h2>
        <p class="text-sm text-muted-foreground">
          Klik "Aktifkan Gate & Selesai" untuk menjalankan daemons dan menandai setup selesai.
        </p>
      </header>
      <ul class="rounded-lg border border-border bg-background p-4 text-sm text-foreground space-y-1">
        <li>✓ Site: {{ form.site.name || '—' }}</li>
        <li>✓ {{ form.tariff.items.length }} jenis kendaraan</li>
        <li>✓ {{ form.areas.length }} area parkir</li>
      </ul>
      <p v-if="finalizeError" class="text-sm text-destructive">{{ finalizeError }}</p>
    </section>

    <!-- Generic error banner -->
    <div
      v-if="errors.generic"
      class="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
    >
      {{ errors.generic }}
    </div>
  </SetupShell>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Button } from '~/components/ui/button'
import { Input } from '~/components/ui/input'
import SetupShell from '~/components/setup/SetupShell.vue'
import TokenGate from '~/components/setup/TokenGate.vue'
import PreflightList from '~/components/setup/PreflightList.vue'
import TariffPresetCard from '~/components/setup/TariffPresetCard.vue'
import WizardField from '~/components/setup/WizardField.vue'
import { useTariffPresets } from '~/composables/useTariffPresets'

definePageMeta({ layout: false })

const route = useRoute()
const router = useRouter()
const { fetchApi } = useApi()
const tariffPresets = useTariffPresets()

const today = new Date().toLocaleDateString('id-ID', { year: 'numeric', month: 'short', day: 'numeric' })

const steps = [
  { key: 'welcome', label: 'Mulai' },
  { key: 'admin', label: 'Admin' },
  { key: 'site', label: 'Lokasi' },
  { key: 'topology', label: 'Topologi' },
  { key: 'gates', label: 'Gate' },
  { key: 'booth', label: 'Booth' },
  { key: 'tariff', label: 'Tarif' },
  { key: 'areas', label: 'Area' },
  { key: 'finalize', label: 'Selesai' },
]

const currentIndex = ref(0)
const step = computed(() => steps[currentIndex.value].key)
const isFinalStep = computed(() => step.value === 'finalize')
const busy = ref(false)
const showHelp = ref(false)
const autosavedLabel = ref('')

const state = reactive({
  topology: 'unknown',
  setup_complete: false,
  has_admin: false,
})

const sessionActive = ref(false)
const tokenLoading = ref(false)
const tokenError = ref('')

const preflight = reactive({ checks: [], passed: 0, warnings: 0, failed: 0 })
const preflightLoading = ref(false)
const finalizeError = ref('')

const form = reactive({
  admin: { username: 'admin', full_name: '', email: '', password: '', confirm: '' },
  site: { name: '', address: '', city: '', phone: '', email: '', tax_id: '' },
  tariff: {
    preset: null,
    items: [],
  },
  areas: [{ name: 'Area Utama', code: 'MAIN', capacity: 100 }],
})

const errors = reactive({ admin: '', tariff: '', areas: '', generic: '' })

const authStore = useAuthStore()

const canAdvance = computed(() => {
  if (step.value === 'welcome') return sessionActive.value && preflight.failed === 0
  if (step.value === 'admin') {
    if (state.has_admin) return true
    return (
      form.admin.username && form.admin.full_name && form.admin.email &&
      form.admin.password && form.admin.password === form.admin.confirm
    )
  }
  if (step.value === 'site') return !!form.site.name
  if (step.value === 'tariff') return form.tariff.items.length > 0
  if (step.value === 'areas') return form.areas.every((a) => a.name && a.code && a.capacity >= 0)
  return true
})

async function refreshState() {
  try {
    const s = await fetchApi('/api/setup/state')
    state.topology = s.topology
    state.setup_complete = s.setup_complete
    state.has_admin = s.has_admin
    sessionActive.value = s.has_session || (!!authStore.user && authStore.user.role === 'admin')
  } catch (err) {
    console.warn('setup_state_failed', err)
  }
}

async function redeemAutoToken() {
  const token = route.query.token
  if (!token) return
  tokenLoading.value = true
  try {
    await fetchApi('/api/setup/redeem-token', {
      method: 'POST',
      body: JSON.stringify({ token }),
    })
    sessionActive.value = true
    tokenError.value = ''
    router.replace({ path: '/setup', query: { ...route.query, token: undefined } })
  } catch (err) {
    tokenError.value = err.message
  } finally {
    tokenLoading.value = false
  }
}

async function redeemManualToken(token) {
  tokenLoading.value = true
  tokenError.value = ''
  try {
    await fetchApi('/api/setup/redeem-token', {
      method: 'POST',
      body: JSON.stringify({ token }),
    })
    sessionActive.value = true
  } catch (err) {
    tokenError.value = err.message
  } finally {
    tokenLoading.value = false
  }
}

async function runPreflight() {
  preflightLoading.value = true
  try {
    const result = await fetchApi('/api/setup/preflight')
    Object.assign(preflight, result)
  } catch (err) {
    errors.generic = `Preflight gagal: ${err.message}`
  } finally {
    preflightLoading.value = false
  }
}

function applyPreset(presetId) {
  const preset = tariffPresets.clonePreset(presetId)
  if (!preset) return
  form.tariff.preset = presetId
  form.tariff.items = preset.items.map((item, idx) => ({
    name: item.name,
    code: item.name.toUpperCase().slice(0, 4) + (idx > 0 ? String(idx) : ''),
    base_tariff: item.first_hour_rate,
    hourly_rate: item.per_hour_rate,
    max_daily_cap: item.daily_cap,
    overnight_mode: 'midnight',
    overnight_tariff: 0,
    lost_ticket_penalty: 0,
    is_progressive: item.rate_type === 'progressive',
  }))
}

function addTariffItem() {
  form.tariff.items.push({
    name: '', code: '', base_tariff: 0, hourly_rate: 0, max_daily_cap: 0,
    overnight_mode: 'midnight', overnight_tariff: 0, lost_ticket_penalty: 0,
    is_progressive: false,
  })
}

function removeTariffItem(idx) {
  form.tariff.items.splice(idx, 1)
}

function addArea() {
  form.areas.push({ name: '', code: '', capacity: 0 })
}

function removeArea(idx) {
  if (form.areas.length <= 1) return
  form.areas.splice(idx, 1)
}

async function persistStep(stepKey, data) {
  if (!sessionActive.value && !(authStore.user && authStore.user.role === 'admin')) return
  try {
    await fetchApi('/api/setup/state', {
      method: 'POST',
      body: JSON.stringify({ step: stepKey, data }),
    })
    autosavedLabel.value = `Tersimpan ${new Date().toLocaleTimeString('id-ID')}`
  } catch (err) {
    console.warn('save_step_failed', err)
  }
}

async function saveCurrentStep() {
  if (step.value === 'admin' && !state.has_admin) {
    if (form.admin.password !== form.admin.confirm) {
      errors.admin = 'Password tidak cocok.'
      return false
    }
    try {
      busy.value = true
      const { confirm, ...payload } = form.admin
      await fetchApi('/api/setup/create-admin', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      state.has_admin = true
      await authStore.fetchUser()
      errors.admin = ''
    } catch (err) {
      errors.admin = err.message
      return false
    } finally {
      busy.value = false
    }
  } else if (step.value === 'site') {
    try {
      busy.value = true
      await fetchApi('/api/site-config', {
        method: 'PUT',
        body: JSON.stringify(form.site),
      })
    } catch (err) {
      errors.generic = `Gagal simpan lokasi: ${err.message}`
      return false
    } finally {
      busy.value = false
    }
  } else if (step.value === 'tariff') {
    if (!form.tariff.items.length) {
      errors.tariff = 'Tambahkan minimal satu jenis kendaraan.'
      return false
    }
    try {
      busy.value = true
      for (const item of form.tariff.items) {
        await fetchApi('/api/vehicle-types', {
          method: 'POST',
          body: JSON.stringify({
            name: item.name,
            code: item.code,
            base_tariff: item.base_tariff,
            hourly_rate: item.hourly_rate,
            max_daily_cap: item.max_daily_cap,
            overnight_mode: item.overnight_mode,
            overnight_tariff: item.overnight_tariff,
            lost_ticket_penalty: item.lost_ticket_penalty,
            is_progressive: item.is_progressive,
          }),
        }).catch((err) => {
          if (err.status !== 409) throw err
        })
      }
      errors.tariff = ''
    } catch (err) {
      errors.tariff = err.message
      return false
    } finally {
      busy.value = false
    }
  } else if (step.value === 'areas') {
    try {
      busy.value = true
      for (const area of form.areas) {
        await fetchApi('/api/areas', {
          method: 'POST',
          body: JSON.stringify(area),
        }).catch((err) => {
          if (err.status !== 409) throw err
        })
      }
      errors.areas = ''
    } catch (err) {
      errors.areas = err.message
      return false
    } finally {
      busy.value = false
    }
  }
  await persistStep(step.value, snapshotForStep(step.value))
  return true
}

function snapshotForStep(stepKey) {
  if (stepKey === 'admin') {
    const { password, confirm, ...safe } = form.admin
    return safe
  }
  if (stepKey === 'site') return { ...form.site }
  if (stepKey === 'tariff') return { preset: form.tariff.preset, items: form.tariff.items }
  if (stepKey === 'areas') return { areas: form.areas }
  return {}
}

async function onNext() {
  errors.generic = ''
  const ok = await saveCurrentStep()
  if (!ok) return
  currentIndex.value = Math.min(steps.length - 1, currentIndex.value + 1)
}

function onBack() {
  currentIndex.value = Math.max(0, currentIndex.value - 1)
}

function onNavigate(idx) {
  if (idx <= currentIndex.value) currentIndex.value = idx
}

async function onFinalize() {
  finalizeError.value = ''
  busy.value = true
  try {
    // P3 endpoint — wired in a later commit. Optimistically attempt it.
    await fetchApi('/api/setup/finalize', { method: 'POST' }).catch(() => null)
    await router.push('/')
  } finally {
    busy.value = false
  }
}

watch(
  () => [form.site, form.admin, form.tariff, form.areas],
  () => { autosavedLabel.value = '' },
  { deep: true },
)

onMounted(async () => {
  await refreshState()
  if (state.setup_complete && route.query.force !== '1' && (!authStore.user || authStore.user.role !== 'admin')) {
    router.replace('/')
    return
  }
  await redeemAutoToken()
  if (state.has_admin) {
    // Skip admin creation step when an admin already exists.
    currentIndex.value = 1
  }
})
</script>
