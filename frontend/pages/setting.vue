<template>
  <div>
    <PageHeader title="Pengaturan" subtitle="Kelola konfigurasi sistem parkir.">
      <template #action>
        <NuxtLink
          v-if="authStore.isAdmin"
          to="/setup?force=1"
          class="inline-flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-2 text-xs font-medium text-foreground hover:bg-surface-hover"
        >
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2Z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
          Jalankan Setup Wizard
        </NuxtLink>
      </template>
    </PageHeader>

    <TabStrip v-model="activeTab" :tabs="tabs" />

    <!-- Site Info -->
    <div v-if="activeTab === 'site-info'" class="max-w-xl space-y-4">
      <div class="space-y-2">
        <label class="text-sm font-medium text-foreground">Site Name</label>
        <Input v-model="siteConfig.name" placeholder="Parking Mall ABC" />
      </div>
      <div class="space-y-2">
        <label class="text-sm font-medium text-foreground">Address</label>
        <textarea v-model="siteConfig.address" rows="2" class="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground" />
      </div>
      <div class="space-y-2">
        <label class="text-sm font-medium text-foreground">City</label>
        <Input v-model="siteConfig.city" />
      </div>
      <div class="space-y-2">
        <label class="text-sm font-medium text-foreground">Phone</label>
        <Input v-model="siteConfig.phone" />
      </div>
      <div class="space-y-2">
        <label class="text-sm font-medium text-foreground">Email</label>
        <Input v-model="siteConfig.email" />
      </div>
      <div class="space-y-2">
        <label class="text-sm font-medium text-foreground">Tax ID (NPWP)</label>
        <Input v-model="siteConfig.tax_id" />
      </div>
      <Button @click="saveSiteConfig">Save</Button>

      <div class="border-t border-border pt-4">
        <h3 class="mb-2 text-sm font-semibold text-foreground">Receipt Preview</h3>
        <div class="rounded-lg border border-border bg-surface p-4 text-center">
          <div class="text-base font-bold text-foreground">{{ siteConfig.name || 'E-Parking' }}</div>
          <div class="text-xs text-muted-foreground">{{ siteConfig.address }}</div>
          <div class="text-xs text-muted-foreground">{{ siteConfig.city }} | {{ siteConfig.phone }}</div>
        </div>
      </div>
    </div>

    <!-- General Settings -->
    <div v-if="activeTab === 'general'">
      <div class="rounded-lg border border-border">
        <div class="grid grid-cols-[200px_1fr_250px_120px] gap-px border-b border-border bg-muted text-xs font-semibold uppercase text-muted-foreground">
          <div class="px-3 py-2">Key</div>
          <div class="px-3 py-2">Label</div>
          <div class="px-3 py-2">Nilai</div>
          <div class="px-3 py-2">Grup</div>
        </div>
        <div v-for="row in settings" :key="row.key" class="grid grid-cols-[200px_1fr_250px_120px] gap-px border-b border-border last:border-0">
          <div class="px-3 py-2 font-mono text-sm text-foreground">{{ row.key }}</div>
          <div class="px-3 py-2 text-sm text-foreground">{{ row.label }}</div>
          <div class="px-3 py-2">
            <input v-model="row.value" class="w-full rounded border border-border bg-background px-2 py-1 text-sm text-foreground" @blur="saveSetting(row)" />
          </div>
          <div class="px-3 py-2">
            <span class="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">{{ row.group }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Vehicle Types -->
    <div v-if="activeTab === 'vehicle-types'">
      <DataTable :data="vehicleTypes" :columns="vehicleTypeColumns" :loading="loadingVehicleTypes" @add="openVehicleTypeModal()" @edit="openVehicleTypeModal" @delete="confirmDeleteVehicleType" />
    </div>

    <!-- Shifts -->
    <div v-if="activeTab === 'shifts'">
      <DataTable :data="shifts" :columns="shiftColumns" :loading="loadingShifts" @add="openShiftModal()" @edit="openShiftModal" @delete="confirmDeleteShift" />
    </div>

    <!-- Areas -->
    <div v-if="activeTab === 'areas'">
      <DataTable :data="areas" :columns="areaColumns" :loading="loadingAreas" @add="openAreaModal()" @edit="openAreaModal" @delete="confirmDeleteArea" />
    </div>

    <!-- Gates Lane Config -->
    <div v-if="activeTab === 'gates'" class="space-y-4">
      <div class="flex items-center justify-between">
        <p class="text-sm text-muted-foreground">Konfigurasi jenis lajur untuk setiap gate keluar (POS).</p>
      </div>
      <div class="rounded-lg border border-border overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-muted">
            <tr>
              <th class="px-3 py-2 text-left text-xs font-semibold uppercase text-muted-foreground">Nama</th>
              <th class="px-3 py-2 text-left text-xs font-semibold uppercase text-muted-foreground w-24">Kode</th>
              <th class="px-3 py-2 text-left text-xs font-semibold uppercase text-muted-foreground w-32">Jenis Lajur</th>
              <th class="px-3 py-2 text-left text-xs font-semibold uppercase text-muted-foreground">Kendaraan Default</th>
              <th class="px-3 py-2 w-20" />
            </tr>
          </thead>
          <tbody>
            <tr v-if="loadingGates" class="border-t border-border">
              <td colspan="5" class="px-3 py-4 text-center text-muted-foreground text-xs">Memuat...</td>
            </tr>
            <tr v-else-if="gateOutList.length === 0" class="border-t border-border">
              <td colspan="5" class="px-3 py-4 text-center text-muted-foreground text-xs">Tidak ada gate keluar</td>
            </tr>
            <tr v-for="gate in gateOutList" :key="gate.id" class="border-t border-border hover:bg-surface/50">
              <td class="px-3 py-2 font-medium text-foreground">{{ gate.name }}</td>
              <td class="px-3 py-2 font-mono text-xs text-muted-foreground">{{ gate.code }}</td>
              <td class="px-3 py-2">
                <span :class="[
                  'rounded-full px-2 py-0.5 text-xs font-medium',
                  gate.hardware_config?.lane_type === 'SINGLE' ? 'bg-primary/10 text-primary' : 'bg-warning/10 text-warning'
                ]">
                  {{ gate.hardware_config?.lane_type === 'SINGLE' ? 'Single' : 'Campuran' }}
                </span>
              </td>
              <td class="px-3 py-2 text-muted-foreground">
                {{ getVehicleTypeName(gate.hardware_config?.default_vehicle_type_id) || '—' }}
              </td>
              <td class="px-3 py-2 text-right">
                <button class="rounded px-2 py-1 text-xs font-medium text-primary hover:bg-primary/10" @click="openGateLaneModal(gate)">Edit</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Gate Lane Config Modal -->
      <Dialog :open="gateLaneModalVisible" @update:open="(v) => { if (!v) gateLaneModalVisible = false }">
        <DialogContent class="max-w-sm">
          <DialogHeader>
            <DialogTitle>Konfigurasi Lajur — {{ editingGate?.name }}</DialogTitle>
          </DialogHeader>

          <div class="space-y-2">
            <label class="text-sm font-medium text-foreground">Jenis Lajur</label>
            <div class="flex gap-3">
              <label v-for="opt in laneTypeOptions" :key="opt.value" class="flex items-center gap-2 cursor-pointer">
                <input type="radio" :value="opt.value" v-model="gateLaneForm.lane_type" class="accent-primary" />
                <span class="text-sm text-foreground">{{ opt.label }}</span>
              </label>
            </div>
            <p class="text-xs text-muted-foreground">
              <span v-if="gateLaneForm.lane_type === 'SINGLE'">Tipe kendaraan otomatis — operator tidak perlu memilih.</span>
              <span v-else>Campuran — operator harus memilih tipe sebelum bayar.</span>
            </p>
          </div>

          <div v-if="gateLaneForm.lane_type === 'SINGLE'" class="space-y-2">
            <label class="text-sm font-medium text-foreground">Jenis Kendaraan Default</label>
            <select v-model.number="gateLaneForm.default_vehicle_type_id" class="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary">
              <option :value="null">— Pilih jenis —</option>
              <option v-for="vt in vehicleTypes" :key="vt.id" :value="vt.id">{{ vt.name }} ({{ vt.code }})</option>
            </select>
          </div>

          <DialogFooter>
            <Button variant="outline" @click="gateLaneModalVisible = false">Batal</Button>
            <Button :disabled="submitting" @click="saveGateLaneConfig">
              {{ submitting ? 'Menyimpan...' : 'Simpan' }}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>

    <!-- Modals -->
    <CrudModal v-model="vehicleTypeModalVisible" :title="vehicleTypeEditing ? 'Edit Jenis Kendaraan' : 'Tambah Jenis Kendaraan'" :fields="vehicleTypeFields" :initial-data="vehicleTypeForm" :submitting="submitting" @submit="saveVehicleType" />
    <CrudModal v-model="shiftModalVisible" :title="shiftEditing ? 'Edit Shift' : 'Tambah Shift'" :fields="shiftFields" :initial-data="shiftForm" :submitting="submitting" @submit="saveShift" />
    <CrudModal v-model="areaModalVisible" :title="areaEditing ? 'Edit Area Parkir' : 'Tambah Area Parkir'" :fields="areaFields" :initial-data="areaForm" :submitting="submitting" @submit="saveArea" />
    <ConfirmDialog v-model="deleteDialogVisible" :title="`Hapus ${deleteTargetName}`" :message="`Apakah Anda yakin ingin menghapus ${deleteTargetName}?`" :loading="submitting" @confirm="executeDelete" />
  </div>
</template>

<script setup>
import { toast } from 'vue-sonner'
import { Button } from '~/components/ui/button'
import { Input } from '~/components/ui/input'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '~/components/ui/dialog'

definePageMeta({ middleware: 'auth' })

const { fetchApi } = useApi()
const authStore = useAuthStore()
const vtCrud = useCrud('/api/vehicle-types', { label: 'Jenis Kendaraan' })
const shiftCrud = useCrud('/api/shifts', { label: 'Shift' })
const areaCrud = useCrud('/api/areas', { label: 'Area Parkir' })

const tabs = [
  { key: 'site-info', label: 'Site Info' },
  { key: 'general', label: 'Umum' },
  { key: 'vehicle-types', label: 'Jenis Kendaraan' },
  { key: 'shifts', label: 'Shift' },
  { key: 'areas', label: 'Area Parkir' },
  { key: 'gates', label: 'Konfigurasi Gate' },
]

const activeTab = ref('general')
const submitting = ref(false)

const siteConfig = ref({ name: '', address: '', city: '', phone: '', email: '', tax_id: '' })
const settings = ref([])

const vehicleTypes = ref([])
const loadingVehicleTypes = ref(false)
const vehicleTypeModalVisible = ref(false)
const vehicleTypeEditing = ref(false)
const vehicleTypeForm = ref({})
const vehicleTypeColumns = [
  { prop: 'name', label: 'Nama', sortable: true },
  { prop: 'code', label: 'Kode', width: 100, sortable: true },
  { prop: 'base_tariff', label: 'Tarif Dasar', width: 120, formatter: (v) => `Rp ${v?.toLocaleString()}` },
  { prop: 'hourly_rate', label: 'Tarif/jam', width: 120, formatter: (v) => `Rp ${v?.toLocaleString()}` },
  { prop: 'max_daily_cap', label: 'Maks Harian', width: 120, formatter: (v) => `Rp ${v?.toLocaleString()}` },
  { prop: 'is_progressive', label: 'Progresif', type: 'boolean', width: 100 },
]
const vehicleTypeFields = [
  { prop: 'name', label: 'Nama', type: 'text', required: true },
  { prop: 'code', label: 'Kode', type: 'text', required: true },
  { prop: 'base_tariff', label: 'Tarif Dasar (IDR)', type: 'number', required: true },
  { prop: 'hourly_rate', label: 'Tarif per Jam (IDR)', type: 'number', required: true },
  { prop: 'max_daily_cap', label: 'Maksimal Harian (IDR)', type: 'number', required: true },
  { prop: 'lost_ticket_penalty', label: 'Denda Tiket Hilang (IDR)', type: 'number' },
  { prop: 'overnight_mode', label: 'Mode Malam', type: 'select', options: [{ label: 'Midnight', value: 'midnight' }, { label: '24 Jam', value: '24h' }, { label: 'Tidak Ada', value: 'none' }] },
  { prop: 'overnight_tariff', label: 'Tarif Malam (IDR)', type: 'number' },
  { prop: 'is_progressive', label: 'Tarif Progresif', type: 'boolean' },
]

const shifts = ref([])
const loadingShifts = ref(false)
const shiftModalVisible = ref(false)
const shiftEditing = ref(false)
const shiftForm = ref({})
const shiftColumns = [
  { prop: 'name', label: 'Nama', sortable: true },
  { prop: 'code', label: 'Kode', width: 120, sortable: true },
  { prop: 'start_time', label: 'Mulai', width: 120 },
  { prop: 'end_time', label: 'Selesai', width: 120 },
  { prop: 'is_active', label: 'Aktif', type: 'boolean', width: 80 },
]
const shiftFields = [
  { prop: 'name', label: 'Nama', type: 'text', required: true },
  { prop: 'code', label: 'Kode', type: 'text', required: true },
  { prop: 'start_time', label: 'Waktu Mulai', type: 'time', required: true },
  { prop: 'end_time', label: 'Waktu Selesai', type: 'time', required: true },
  { prop: 'is_active', label: 'Aktif', type: 'boolean' },
  { prop: 'description', label: 'Keterangan', type: 'textarea' },
]

const areas = ref([])
const loadingAreas = ref(false)
const areaModalVisible = ref(false)
const areaEditing = ref(false)
const areaForm = ref({})
const areaColumns = [
  { prop: 'name', label: 'Nama', sortable: true },
  { prop: 'code', label: 'Kode', width: 120, sortable: true },
  { prop: 'capacity', label: 'Kapasitas', width: 120, sortable: true },
  { prop: 'current', label: 'Terisi', width: 100, sortable: true },
  { prop: 'description', label: 'Keterangan' },
]
const areaFields = [
  { prop: 'name', label: 'Nama', type: 'text', required: true },
  { prop: 'code', label: 'Kode', type: 'text', required: true },
  { prop: 'capacity', label: 'Kapasitas', type: 'number', required: true },
  { prop: 'current', label: 'Terisi', type: 'number' },
  { prop: 'description', label: 'Keterangan', type: 'textarea' },
]

const deleteDialogVisible = ref(false)
const deleteTargetName = ref('')
const deleteAction = ref(null)

const gateOutList = ref([])
const loadingGates = ref(false)
const gateLaneModalVisible = ref(false)
const editingGate = ref(null)
const gateLaneForm = ref({ lane_type: 'MIXED', default_vehicle_type_id: null })
const laneTypeOptions = [
  { value: 'MIXED', label: 'Campuran' },
  { value: 'SINGLE', label: 'Single' },
]

function getVehicleTypeName(id) {
  if (!id) return null
  return vehicleTypes.value.find((v) => v.id === id)?.name || null
}

function openGateLaneModal(gate) {
  editingGate.value = gate
  gateLaneForm.value = {
    lane_type: gate.hardware_config?.lane_type || 'MIXED',
    default_vehicle_type_id: gate.hardware_config?.default_vehicle_type_id || null,
  }
  gateLaneModalVisible.value = true
}

async function saveGateLaneConfig() {
  submitting.value = true
  try {
    await fetchApi(`/api/gates/${editingGate.value.id}/lane-config`, {
      method: 'PATCH',
      body: JSON.stringify(gateLaneForm.value),
    })
    gateLaneModalVisible.value = false
    await loadGates()
    toast.success('Konfigurasi lajur tersimpan')
  } catch (e) {
    toast.error(`Gagal menyimpan konfigurasi lajur: ${e.message}`)
  } finally {
    submitting.value = false
  }
}

async function loadGates() {
  loadingGates.value = true
  try {
    gateOutList.value = await fetchApi('/api/gates?direction=OUT')
  } catch (e) {
    console.error(e)
  } finally {
    loadingGates.value = false
  }
}

onMounted(() => { loadSiteConfig(); loadSettings(); loadVehicleTypes(); loadShifts(); loadAreas(); loadGates() })

async function loadSiteConfig() { try { const { data } = await fetchApi('/api/site-config'); siteConfig.value = data } catch (e) { /* ok */ } }
async function saveSiteConfig() {
  try {
    await fetchApi('/api/site-config', { method: 'PUT', body: JSON.stringify(siteConfig.value) })
    toast.success('Info site tersimpan')
  } catch (e) {
    toast.error(`Gagal menyimpan info site: ${e.message}`)
  }
}
// Snapshot of last-saved values so an invalid edit or failed save can revert.
const _settingOriginals = {}
async function loadSettings() {
  try {
    settings.value = await fetchApi('/api/settings')
    for (const row of settings.value) _settingOriginals[row.key] = row.value
  } catch (e) { console.error(e) }
}
async function saveSetting(row) {
  const original = _settingOriginals[row.key]
  // No change — skip the round-trip.
  if (row.value === original) return
  // If the setting was previously numeric, the new value must be a
  // non-negative number. Reject silently-bad input before it reaches the API.
  const wasNumeric = original !== '' && original != null && !Number.isNaN(Number(original))
  if (wasNumeric) {
    const n = Number(row.value)
    if (Number.isNaN(n) || n < 0) {
      toast.error(`Nilai "${row.label || row.key}" harus angka ≥ 0`)
      row.value = original
      return
    }
  }
  try {
    await fetchApi(`/api/settings/${row.key}`, { method: 'PATCH', body: JSON.stringify({ value: row.value }) })
    _settingOriginals[row.key] = row.value
    toast.success(`"${row.label || row.key}" tersimpan`)
  } catch (e) {
    console.error(e)
    toast.error(`Gagal menyimpan "${row.label || row.key}"`)
    row.value = original
  }
}

async function loadVehicleTypes() { loadingVehicleTypes.value = true; try { vehicleTypes.value = await vtCrud.list() } catch (e) { console.error(e) } finally { loadingVehicleTypes.value = false } }
function openVehicleTypeModal(row = null) { vehicleTypeEditing.value = !!row; vehicleTypeForm.value = row ? { ...row } : {}; vehicleTypeModalVisible.value = true }
async function saveVehicleType(data) { submitting.value = true; try { if (vehicleTypeEditing.value) await vtCrud.update(data.id, data); else await vtCrud.create(data); vehicleTypeModalVisible.value = false; await loadVehicleTypes() } catch (e) { console.error(e) } finally { submitting.value = false } }
function confirmDeleteVehicleType(row) { deleteTargetName.value = row.name; deleteAction.value = () => deleteVehicleType(row.id); deleteDialogVisible.value = true }
async function deleteVehicleType(id) { submitting.value = true; try { await vtCrud.remove(id); deleteDialogVisible.value = false; await loadVehicleTypes() } catch (e) { console.error(e) } finally { submitting.value = false } }

async function loadShifts() { loadingShifts.value = true; try { shifts.value = await shiftCrud.list() } catch (e) { console.error(e) } finally { loadingShifts.value = false } }
function openShiftModal(row = null) { shiftEditing.value = !!row; shiftForm.value = row ? { ...row } : {}; shiftModalVisible.value = true }
async function saveShift(data) { submitting.value = true; try { if (shiftEditing.value) await shiftCrud.update(data.id, data); else await shiftCrud.create(data); shiftModalVisible.value = false; await loadShifts() } catch (e) { console.error(e) } finally { submitting.value = false } }
function confirmDeleteShift(row) { deleteTargetName.value = row.name; deleteAction.value = () => deleteShift(row.id); deleteDialogVisible.value = true }
async function deleteShift(id) { submitting.value = true; try { await shiftCrud.remove(id); deleteDialogVisible.value = false; await loadShifts() } catch (e) { console.error(e) } finally { submitting.value = false } }

async function loadAreas() { loadingAreas.value = true; try { areas.value = await areaCrud.list() } catch (e) { console.error(e) } finally { loadingAreas.value = false } }
function openAreaModal(row = null) { areaEditing.value = !!row; areaForm.value = row ? { ...row } : {}; areaModalVisible.value = true }
async function saveArea(data) { submitting.value = true; try { if (areaEditing.value) await areaCrud.update(data.id, data); else await areaCrud.create(data); areaModalVisible.value = false; await loadAreas() } catch (e) { console.error(e) } finally { submitting.value = false } }
function confirmDeleteArea(row) { deleteTargetName.value = row.name; deleteAction.value = () => deleteArea(row.id); deleteDialogVisible.value = true }
async function deleteArea(id) { submitting.value = true; try { await areaCrud.remove(id); deleteDialogVisible.value = false; await loadAreas() } catch (e) { console.error(e) } finally { submitting.value = false } }

function executeDelete() { if (deleteAction.value) deleteAction.value() }
</script>
