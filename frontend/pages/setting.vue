<template>
  <div>
    <h1>Pengaturan</h1>
    <p class="text-secondary mb-3">Kelola konfigurasi sistem parkir.</p>

    <el-tabs v-model="activeTab" type="border-card">
      <!-- Site Info -->
      <el-tab-pane label="Site Info" name="site-info">
        <el-form :model="siteConfig" label-width="120px">
          <el-form-item label="Site Name">
            <el-input v-model="siteConfig.name" placeholder="Parking Mall ABC" />
          </el-form-item>
          <el-form-item label="Address">
            <el-input v-model="siteConfig.address" type="textarea" rows="2" />
          </el-form-item>
          <el-form-item label="City">
            <el-input v-model="siteConfig.city" />
          </el-form-item>
          <el-form-item label="Phone">
            <el-input v-model="siteConfig.phone" />
          </el-form-item>
          <el-form-item label="Email">
            <el-input v-model="siteConfig.email" />
          </el-form-item>
          <el-form-item label="Tax ID (NPWP)">
            <el-input v-model="siteConfig.tax_id" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveSiteConfig">Save</el-button>
          </el-form-item>
        </el-form>

        <el-divider />

        <h4>Receipt Preview</h4>
        <el-card class="receipt-preview">
          <div class="text-center">
            <h3>{{ siteConfig.name || 'E-Parking' }}</h3>
            <p class="text-small">{{ siteConfig.address }}</p>
            <p class="text-small">{{ siteConfig.city }} | {{ siteConfig.phone }}</p>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- General Settings -->
      <el-tab-pane label="Umum" name="general">
        <el-table :data="settings" stripe style="width: 100%">
          <el-table-column prop="key" label="Key" width="200" />
          <el-table-column prop="label" label="Label" />
          <el-table-column prop="value" label="Nilai" width="250">
            <template #default="{ row }">
              <el-input
                v-model="row.value"
                size="small"
                @blur="saveSetting(row)"
              />
            </template>
          </el-table-column>
          <el-table-column prop="group" label="Grup" width="120">
            <template #default="{ row }">
              <el-tag size="small">{{ row.group }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Vehicle Types -->
      <el-tab-pane label="Jenis Kendaraan" name="vehicle-types">
        <DataTable
          :data="vehicleTypes"
          :columns="vehicleTypeColumns"
          :loading="loadingVehicleTypes"
          @add="openVehicleTypeModal()"
          @edit="openVehicleTypeModal"
          @delete="confirmDeleteVehicleType"
        />
      </el-tab-pane>

      <!-- Shifts -->
      <el-tab-pane label="Shift" name="shifts">
        <DataTable
          :data="shifts"
          :columns="shiftColumns"
          :loading="loadingShifts"
          @add="openShiftModal()"
          @edit="openShiftModal"
          @delete="confirmDeleteShift"
        />
      </el-tab-pane>

      <!-- Areas -->
      <el-tab-pane label="Area Parkir" name="areas">
        <DataTable
          :data="areas"
          :columns="areaColumns"
          :loading="loadingAreas"
          @add="openAreaModal()"
          @edit="openAreaModal"
          @delete="confirmDeleteArea"
        />
      </el-tab-pane>
    </el-tabs>

    <!-- Vehicle Type Modal -->
    <CrudModal
      v-model="vehicleTypeModalVisible"
      :title="vehicleTypeEditing ? 'Edit Jenis Kendaraan' : 'Tambah Jenis Kendaraan'"
      :fields="vehicleTypeFields"
      :initial-data="vehicleTypeForm"
      :submitting="submitting"
      @submit="saveVehicleType"
    />

    <!-- Shift Modal -->
    <CrudModal
      v-model="shiftModalVisible"
      :title="shiftEditing ? 'Edit Shift' : 'Tambah Shift'"
      :fields="shiftFields"
      :initial-data="shiftForm"
      :submitting="submitting"
      @submit="saveShift"
    />

    <!-- Area Modal -->
    <CrudModal
      v-model="areaModalVisible"
      :title="areaEditing ? 'Edit Area Parkir' : 'Tambah Area Parkir'"
      :fields="areaFields"
      :initial-data="areaForm"
      :submitting="submitting"
      @submit="saveArea"
    />

    <!-- Delete Confirm -->
    <ConfirmDialog
      v-model="deleteDialogVisible"
      :title="`Hapus ${deleteTargetName}`"
      :message="`Apakah Anda yakin ingin menghapus ${deleteTargetName}?`"
      :loading="submitting"
      @confirm="executeDelete"
    />
  </div>
</template>

<script setup>
definePageMeta({
  middleware: 'auth',
})

const { fetchApi } = useApi()
const vtCrud = useCrud('/api/vehicle-types')
const shiftCrud = useCrud('/api/shifts')
const areaCrud = useCrud('/api/areas')

const activeTab = ref('general')
const submitting = ref(false)

// Site Config
const siteConfig = ref({
  name: '',
  address: '',
  city: '',
  phone: '',
  email: '',
  tax_id: '',
})

// Settings
const settings = ref([])

// Vehicle Types
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
  { prop: 'overnight_mode', label: 'Mode Malam', type: 'select', options: [
    { label: 'Midnight', value: 'midnight' },
    { label: '24 Jam', value: '24h' },
    { label: 'Tidak Ada', value: 'none' },
  ]},
  { prop: 'overnight_tariff', label: 'Tarif Malam (IDR)', type: 'number' },
  { prop: 'is_progressive', label: 'Tarif Progresif', type: 'boolean' },
]

// Shifts
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

// Areas
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

// Delete dialog
const deleteDialogVisible = ref(false)
const deleteTargetName = ref('')
const deleteAction = ref(null)

// Load data
onMounted(() => {
  loadSiteConfig()
  loadSettings()
  loadVehicleTypes()
  loadShifts()
  loadAreas()
})

async function loadSiteConfig() {
  try {
    const { data } = await fetchApi('/api/site-config')
    siteConfig.value = data
  } catch (e) {
    if (e.response?.status !== 404) {
      console.error('Failed to load site config', e)
    }
  }
}

async function saveSiteConfig() {
  try {
    await fetchApi('/api/site-config', {
      method: 'PUT',
      body: JSON.stringify(siteConfig.value),
    })
    ElMessage.success('Site config saved')
  } catch (e) {
    ElMessage.error('Failed to save site config')
  }
}

async function loadSettings() {
  try {
    settings.value = await fetchApi('/api/settings')
  } catch (err) {
    ElMessage.error('Gagal memuat pengaturan')
  }
}

async function saveSetting(row) {
  try {
    await fetchApi(`/api/settings/${row.key}`, {
      method: 'PATCH',
      body: JSON.stringify({ value: row.value }),
    })
    ElMessage.success('Pengaturan disimpan')
  } catch (err) {
    ElMessage.error('Gagal menyimpan pengaturan')
  }
}

// Vehicle Types
async function loadVehicleTypes() {
  loadingVehicleTypes.value = true
  try {
    vehicleTypes.value = await vtCrud.list()
  } catch (err) {
    ElMessage.error('Gagal memuat jenis kendaraan')
  } finally {
    loadingVehicleTypes.value = false
  }
}

function openVehicleTypeModal(row = null) {
  vehicleTypeEditing.value = !!row
  vehicleTypeForm.value = row ? { ...row } : {}
  vehicleTypeModalVisible.value = true
}

async function saveVehicleType(data) {
  submitting.value = true
  try {
    if (vehicleTypeEditing.value) {
      await vtCrud.update(data.id, data)
    } else {
      await vtCrud.create(data)
    }
    vehicleTypeModalVisible.value = false
    await loadVehicleTypes()
    ElMessage.success('Jenis kendaraan disimpan')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menyimpan')
  } finally {
    submitting.value = false
  }
}

function confirmDeleteVehicleType(row) {
  deleteTargetName.value = row.name
  deleteAction.value = () => deleteVehicleType(row.id)
  deleteDialogVisible.value = true
}

async function deleteVehicleType(id) {
  submitting.value = true
  try {
    await vtCrud.remove(id)
    deleteDialogVisible.value = false
    await loadVehicleTypes()
    ElMessage.success('Jenis kendaraan dihapus')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menghapus')
  } finally {
    submitting.value = false
  }
}

// Shifts
async function loadShifts() {
  loadingShifts.value = true
  try {
    shifts.value = await shiftCrud.list()
  } catch (err) {
    ElMessage.error('Gagal memuat shift')
  } finally {
    loadingShifts.value = false
  }
}

function openShiftModal(row = null) {
  shiftEditing.value = !!row
  shiftForm.value = row ? { ...row } : {}
  shiftModalVisible.value = true
}

async function saveShift(data) {
  submitting.value = true
  try {
    if (shiftEditing.value) {
      await shiftCrud.update(data.id, data)
    } else {
      await shiftCrud.create(data)
    }
    shiftModalVisible.value = false
    await loadShifts()
    ElMessage.success('Shift disimpan')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menyimpan')
  } finally {
    submitting.value = false
  }
}

function confirmDeleteShift(row) {
  deleteTargetName.value = row.name
  deleteAction.value = () => deleteShift(row.id)
  deleteDialogVisible.value = true
}

async function deleteShift(id) {
  submitting.value = true
  try {
    await shiftCrud.remove(id)
    deleteDialogVisible.value = false
    await loadShifts()
    ElMessage.success('Shift dihapus')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menghapus')
  } finally {
    submitting.value = false
  }
}

// Areas
async function loadAreas() {
  loadingAreas.value = true
  try {
    areas.value = await areaCrud.list()
  } catch (err) {
    ElMessage.error('Gagal memuat area parkir')
  } finally {
    loadingAreas.value = false
  }
}

function openAreaModal(row = null) {
  areaEditing.value = !!row
  areaForm.value = row ? { ...row } : {}
  areaModalVisible.value = true
}

async function saveArea(data) {
  submitting.value = true
  try {
    if (areaEditing.value) {
      await areaCrud.update(data.id, data)
    } else {
      await areaCrud.create(data)
    }
    areaModalVisible.value = false
    await loadAreas()
    ElMessage.success('Area parkir disimpan')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menyimpan')
  } finally {
    submitting.value = false
  }
}

function confirmDeleteArea(row) {
  deleteTargetName.value = row.name
  deleteAction.value = () => deleteArea(row.id)
  deleteDialogVisible.value = true
}

async function deleteArea(id) {
  submitting.value = true
  try {
    await areaCrud.remove(id)
    deleteDialogVisible.value = false
    await loadAreas()
    ElMessage.success('Area parkir dihapus')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menghapus')
  } finally {
    submitting.value = false
  }
}

// Generic delete execution
function executeDelete() {
  if (deleteAction.value) deleteAction.value()
}
</script>
