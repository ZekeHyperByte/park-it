<template>
  <div>
    <h1>Perangkat</h1>
    <p class="text-secondary mb-3">Manajemen gate, booth POS, kamera, printer, dan e-money reader.</p>

    <el-tabs v-model="activeTab" type="border-card">
      <!-- Gates -->
      <el-tab-pane label="Gates" name="gates">
        <DataTable
          :data="gates"
          :columns="gateColumns"
          :loading="loadingGates"
          @add="openGateModal()"
          @edit="openGateModal"
          @delete="confirmDeleteGate"
        />
      </el-tab-pane>

      <!-- POS Booths -->
      <el-tab-pane label="Booth POS" name="pos">
        <DataTable
          :data="posList"
          :columns="posColumns"
          :loading="loadingPos"
          @add="openPosModal()"
          @edit="openPosModal"
          @delete="confirmDeletePos"
        />
      </el-tab-pane>

      <!-- Cameras -->
      <el-tab-pane label="Kamera" name="cameras">
        <DataTable
          :data="cameras"
          :columns="cameraColumns"
          :loading="loadingCameras"
          @add="openCameraModal()"
          @edit="openCameraModal"
          @delete="confirmDeleteCamera"
        />
      </el-tab-pane>

      <!-- Printers -->
      <el-tab-pane label="Printer" name="printers">
        <DataTable
          :data="printers"
          :columns="printerColumns"
          :loading="loadingPrinters"
          @add="openPrinterModal()"
          @edit="openPrinterModal"
          @delete="confirmDeletePrinter"
        />
      </el-tab-pane>

      <!-- E-Money Readers -->
      <el-tab-pane label="E-Money Reader" name="emoney-readers">
        <DataTable
          :data="emoneyReaders"
          :columns="emoneyReaderColumns"
          :loading="loadingEmoneyReaders"
          @add="openEmoneyReaderModal()"
          @edit="openEmoneyReaderModal"
          @delete="confirmDeleteEmoneyReader"
        />
      </el-tab-pane>
    </el-tabs>

    <!-- Gate Modal -->
    <CrudModal
      v-model="gateModalVisible"
      :title="gateEditing ? 'Edit Gate' : 'Tambah Gate'"
      :fields="gateFields"
      :initial-data="gateForm"
      :submitting="submitting"
      @submit="saveGate"
    />

    <!-- POS Modal -->
    <CrudModal
      v-model="posModalVisible"
      :title="posEditing ? 'Edit Booth POS' : 'Tambah Booth POS'"
      :fields="posFields"
      :initial-data="posForm"
      :submitting="submitting"
      @submit="savePos"
    />

    <!-- Camera Modal -->
    <CrudModal
      v-model="cameraModalVisible"
      :title="cameraEditing ? 'Edit Kamera' : 'Tambah Kamera'"
      :fields="cameraFields"
      :initial-data="cameraForm"
      :submitting="submitting"
      @submit="saveCamera"
    />

    <!-- Printer Modal -->
    <CrudModal
      v-model="printerModalVisible"
      :title="printerEditing ? 'Edit Printer' : 'Tambah Printer'"
      :fields="printerFields"
      :initial-data="printerForm"
      :submitting="submitting"
      @submit="savePrinter"
    />

    <!-- E-Money Reader Modal -->
    <CrudModal
      v-model="emoneyReaderModalVisible"
      :title="emoneyReaderEditing ? 'Edit E-Money Reader' : 'Tambah E-Money Reader'"
      :fields="emoneyReaderFields"
      :initial-data="emoneyReaderForm"
      :submitting="submitting"
      @submit="saveEmoneyReader"
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
const gateCrud = useCrud('/api/gates')
const posCrud = useCrud('/api/pos')
const cameraCrud = useCrud('/api/cameras')
const printerCrud = useCrud('/api/printers')
const readerCrud = useCrud('/api/emoney-readers')

const activeTab = ref('gates')
const submitting = ref(false)

// ─────────────────────────────────────────────────────────────────────────────
// Gates
// ─────────────────────────────────────────────────────────────────────────────
const gates = ref([])
const loadingGates = ref(false)
const gateModalVisible = ref(false)
const gateEditing = ref(false)
const gateForm = ref({})

const gateColumns = [
  { prop: 'name', label: 'Nama', sortable: true },
  { prop: 'code', label: 'Kode', width: 120, sortable: true },
  { prop: 'direction', label: 'Arah', width: 80, type: 'enum' },
  { prop: 'protocol', label: 'Protokol', width: 100 },
  { prop: 'controller_host', label: 'Controller', width: 150 },
  { prop: 'is_active', label: 'Aktif', type: 'boolean', width: 80 },
]

const gateFields = computed(() => {
  const base = [
    { prop: 'name', label: 'Nama', type: 'text', required: true },
    { prop: 'code', label: 'Kode', type: 'text', required: true },
    { prop: 'direction', label: 'Arah', type: 'select', required: true, options: [
      { label: 'Masuk', value: 'IN' },
      { label: 'Keluar', value: 'OUT' },
    ]},
    { prop: 'protocol', label: 'Protokol', type: 'select', required: true, options: [
      { label: 'Compass', value: 'compass' },
      { label: 'ENET', value: 'enet' },
      { label: 'Serial', value: 'serial' },
    ]},
    { prop: 'controller_host', label: 'Host Controller', type: 'text' },
    { prop: 'controller_port', label: 'Port Controller', type: 'number' },
    { prop: 'controller_device', label: 'Device Controller', type: 'text' },
    { prop: 'controller_baudrate', label: 'Baudrate Controller', type: 'number' },
    { prop: 'has_close_sensor', label: 'Sensor Tutup', type: 'boolean' },
    { prop: 'relay_mode', label: 'Mode Relay', type: 'select', options: [
      { label: 'Single', value: 'SINGLE' },
      { label: 'Dual', value: 'DUAL' },
    ]},
  ]

  // Direction-specific peripherals
  const dir = gateForm.value.direction
  if (dir === 'IN') {
    base.push(
      { prop: '_rfid_enabled', label: 'RFID Reader', type: 'boolean' },
      { prop: '_ticket_printer_enabled', label: 'Printer Tiket', type: 'boolean' },
      { prop: '_emoney_enabled', label: 'E-Money', type: 'boolean' },
      { prop: '_camera_enabled', label: 'Kamera', type: 'boolean' },
    )
  } else if (dir === 'OUT') {
    base.push(
      { prop: 'pos_id', label: 'Booth POS', type: 'number' },
      { prop: '_uhf_reader_enabled', label: 'UHF Reader', type: 'boolean' },
      { prop: '_camera_enabled', label: 'Kamera', type: 'boolean' },
    )
  }

  base.push({ prop: 'is_active', label: 'Aktif', type: 'boolean' })
  return base
})

function flattenHardwareConfig(hw = {}) {
  return {
    _rfid_enabled: hw.rfid?.enabled ?? false,
    _ticket_printer_enabled: hw.ticket_printer?.enabled ?? false,
    _emoney_enabled: hw.emoney?.enabled ?? false,
    _camera_enabled: hw.camera?.enabled ?? false,
    _uhf_reader_enabled: hw.uhf_reader?.enabled ?? false,
  }
}

function buildHardwareConfig(form) {
  const hw = {}
  if (form._rfid_enabled !== undefined) {
    hw.rfid = { enabled: form._rfid_enabled, wiegand_channel: 'W' }
  }
  if (form._ticket_printer_enabled !== undefined) {
    hw.ticket_printer = { enabled: form._ticket_printer_enabled }
  }
  if (form._emoney_enabled !== undefined) {
    hw.emoney = { enabled: form._emoney_enabled, minimum_balance: 10000 }
  }
  if (form._camera_enabled !== undefined) {
    hw.camera = { enabled: form._camera_enabled }
  }
  if (form._uhf_reader_enabled !== undefined) {
    hw.uhf_reader = { enabled: form._uhf_reader_enabled }
  }
  return hw
}

function openGateModal(row = null) {
  gateEditing.value = !!row
  if (row) {
    gateForm.value = { ...row, ...flattenHardwareConfig(row.hardware_config) }
  } else {
    gateForm.value = { direction: 'IN', protocol: 'compass', relay_mode: 'SINGLE', has_close_sensor: false, is_active: true }
  }
  gateModalVisible.value = true
}

async function saveGate(data) {
  submitting.value = true
  try {
    const payload = { ...data }
    payload.hardware_config = buildHardwareConfig(data)
    // Remove internal flattened fields
    delete payload._rfid_enabled
    delete payload._ticket_printer_enabled
    delete payload._emoney_enabled
    delete payload._camera_enabled
    delete payload._uhf_reader_enabled

    if (gateEditing.value) {
      await gateCrud.update(data.id, payload)
    } else {
      await gateCrud.create(payload)
    }
    gateModalVisible.value = false
    await loadGates()
    ElMessage.success('Gate disimpan')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menyimpan')
  } finally {
    submitting.value = false
  }
}

function confirmDeleteGate(row) {
  deleteTargetName.value = row.name
  deleteAction.value = () => deleteGate(row.id)
  deleteDialogVisible.value = true
}

async function deleteGate(id) {
  submitting.value = true
  try {
    await gateCrud.remove(id)
    deleteDialogVisible.value = false
    await loadGates()
    ElMessage.success('Gate dihapus')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menghapus')
  } finally {
    submitting.value = false
  }
}

async function loadGates() {
  loadingGates.value = true
  try {
    gates.value = await gateCrud.list()
  } catch (err) {
    ElMessage.error('Gagal memuat gates')
  } finally {
    loadingGates.value = false
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// POS Booths
// ─────────────────────────────────────────────────────────────────────────────
const posList = ref([])
const loadingPos = ref(false)
const posModalVisible = ref(false)
const posEditing = ref(false)
const posForm = ref({})

const posColumns = [
  { prop: 'name', label: 'Nama', sortable: true },
  { prop: 'code', label: 'Kode', width: 120, sortable: true },
  { prop: 'ip_address', label: 'IP Address', width: 150 },
  { prop: 'default_gate_id', label: 'Gate Default', width: 120 },
  { prop: 'is_active', label: 'Aktif', type: 'boolean', width: 80 },
]

const posFields = [
  { prop: 'name', label: 'Nama', type: 'text', required: true },
  { prop: 'code', label: 'Kode', type: 'text', required: true },
  { prop: 'ip_address', label: 'IP Address', type: 'text' },
  { prop: 'default_gate_id', label: 'Gate Default (ID)', type: 'number' },
  { prop: 'is_active', label: 'Aktif', type: 'boolean' },
]

function openPosModal(row = null) {
  posEditing.value = !!row
  posForm.value = row ? { ...row } : { is_active: true }
  posModalVisible.value = true
}

async function savePos(data) {
  submitting.value = true
  try {
    if (posEditing.value) {
      await posCrud.update(data.id, data)
    } else {
      await posCrud.create(data)
    }
    posModalVisible.value = false
    await loadPos()
    ElMessage.success('Booth POS disimpan')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menyimpan')
  } finally {
    submitting.value = false
  }
}

function confirmDeletePos(row) {
  deleteTargetName.value = row.name
  deleteAction.value = () => deletePos(row.id)
  deleteDialogVisible.value = true
}

async function deletePos(id) {
  submitting.value = true
  try {
    await posCrud.remove(id)
    deleteDialogVisible.value = false
    await loadPos()
    ElMessage.success('Booth POS dihapus')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menghapus')
  } finally {
    submitting.value = false
  }
}

async function loadPos() {
  loadingPos.value = true
  try {
    posList.value = await posCrud.list()
  } catch (err) {
    ElMessage.error('Gagal memuat booth POS')
  } finally {
    loadingPos.value = false
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Cameras
// ─────────────────────────────────────────────────────────────────────────────
const cameras = ref([])
const loadingCameras = ref(false)
const cameraModalVisible = ref(false)
const cameraEditing = ref(false)
const cameraForm = ref({})

const cameraColumns = [
  { prop: 'name', label: 'Nama', sortable: true },
  { prop: 'rtsp_url', label: 'RTSP URL', width: 250 },
  { prop: 'type', label: 'Tipe', width: 80 },
  { prop: 'is_active', label: 'Aktif', type: 'boolean', width: 80 },
]

const cameraFields = [
  { prop: 'name', label: 'Nama', type: 'text', required: true },
  { prop: 'rtsp_url', label: 'RTSP URL', type: 'text' },
  { prop: 'snapshot_url', label: 'Snapshot URL', type: 'text' },
  { prop: 'username', label: 'Username', type: 'text' },
  { prop: 'password', label: 'Password', type: 'text' },
  { prop: 'type', label: 'Tipe', type: 'select', options: [
    { label: 'RTSP', value: 'rtsp' },
    { label: 'ONVIF', value: 'onvif' },
  ]},
  { prop: 'is_active', label: 'Aktif', type: 'boolean' },
]

function openCameraModal(row = null) {
  cameraEditing.value = !!row
  cameraForm.value = row ? { ...row } : { type: 'rtsp', is_active: true }
  cameraModalVisible.value = true
}

async function saveCamera(data) {
  submitting.value = true
  try {
    if (cameraEditing.value) {
      await cameraCrud.update(data.id, data)
    } else {
      await cameraCrud.create(data)
    }
    cameraModalVisible.value = false
    await loadCameras()
    ElMessage.success('Kamera disimpan')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menyimpan')
  } finally {
    submitting.value = false
  }
}

function confirmDeleteCamera(row) {
  deleteTargetName.value = row.name
  deleteAction.value = () => deleteCamera(row.id)
  deleteDialogVisible.value = true
}

async function deleteCamera(id) {
  submitting.value = true
  try {
    await cameraCrud.remove(id)
    deleteDialogVisible.value = false
    await loadCameras()
    ElMessage.success('Kamera dihapus')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menghapus')
  } finally {
    submitting.value = false
  }
}

async function loadCameras() {
  loadingCameras.value = true
  try {
    cameras.value = await cameraCrud.list()
  } catch (err) {
    ElMessage.error('Gagal memuat kamera')
  } finally {
    loadingCameras.value = false
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Printers
// ─────────────────────────────────────────────────────────────────────────────
const printers = ref([])
const loadingPrinters = ref(false)
const printerModalVisible = ref(false)
const printerEditing = ref(false)
const printerForm = ref({})

const printerColumns = [
  { prop: 'name', label: 'Nama', sortable: true },
  { prop: 'mode', label: 'Mode', width: 150 },
  { prop: 'gate_id', label: 'Gate ID', width: 120 },
  { prop: 'pos_id', label: 'POS ID', width: 100 },
  { prop: 'paper_remaining', label: 'Sisa Kertas', width: 110 },
  { prop: 'is_active', label: 'Aktif', type: 'boolean', width: 80 },
]

const printerFields = [
  { prop: 'name', label: 'Nama', type: 'text', required: true },
  { prop: 'mode', label: 'Mode', type: 'select', required: true, options: [
    { label: 'Controller Passthrough', value: 'CONTROLLER_PASSTHROUGH' },
    { label: 'Network', value: 'NETWORK' },
    { label: 'Serial', value: 'SERIAL' },
  ]},
  { prop: 'ip_address', label: 'IP Address', type: 'text' },
  { prop: 'port', label: 'Port', type: 'number' },
  { prop: 'serial_device', label: 'Device Serial', type: 'text' },
  { prop: 'baudrate', label: 'Baudrate', type: 'number' },
  { prop: 'pos_id', label: 'POS ID', type: 'number' },
  { prop: 'is_active', label: 'Aktif', type: 'boolean' },
]

function openPrinterModal(row = null) {
  printerEditing.value = !!row
  printerForm.value = row ? { ...row } : { mode: 'CONTROLLER_PASSTHROUGH', baudrate: 9600, is_active: true }
  printerModalVisible.value = true
}

async function savePrinter(data) {
  submitting.value = true
  try {
    if (printerEditing.value) {
      await printerCrud.update(data.id, data)
    } else {
      await printerCrud.create(data)
    }
    printerModalVisible.value = false
    await loadPrinters()
    ElMessage.success('Printer disimpan')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menyimpan')
  } finally {
    submitting.value = false
  }
}

function confirmDeletePrinter(row) {
  deleteTargetName.value = row.name
  deleteAction.value = () => deletePrinter(row.id)
  deleteDialogVisible.value = true
}

async function deletePrinter(id) {
  submitting.value = true
  try {
    await printerCrud.remove(id)
    deleteDialogVisible.value = false
    await loadPrinters()
    ElMessage.success('Printer dihapus')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menghapus')
  } finally {
    submitting.value = false
  }
}

async function loadPrinters() {
  loadingPrinters.value = true
  try {
    printers.value = await printerCrud.list()
  } catch (err) {
    ElMessage.error('Gagal memuat printer')
  } finally {
    loadingPrinters.value = false
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// E-Money Readers (kept from original)
// ─────────────────────────────────────────────────────────────────────────────
const emoneyReaders = ref([])
const loadingEmoneyReaders = ref(false)
const emoneyReaderModalVisible = ref(false)
const emoneyReaderEditing = ref(false)
const emoneyReaderForm = ref({})

const emoneyReaderColumns = [
  { prop: 'name', label: 'Nama', sortable: true },
  { prop: 'code', label: 'Kode', width: 120, sortable: true },
  { prop: 'serial_port', label: 'Port Serial', width: 150 },
  { prop: 'baudrate', label: 'Baudrate', width: 100 },
  { prop: 'connection_type', label: 'Koneksi', width: 150, type: 'enum' },
  { prop: 'is_online', label: 'Online', type: 'boolean', width: 80 },
  { prop: 'is_active', label: 'Aktif', type: 'boolean', width: 80 },
]

const emoneyReaderFields = [
  { prop: 'name', label: 'Nama', type: 'text', required: true },
  { prop: 'code', label: 'Kode', type: 'text', required: true },
  { prop: 'connection_type', label: 'Tipe Koneksi', type: 'select', required: true, options: [
    { label: 'Controller Passthrough', value: 'CONTROLLER_PASSTHROUGH' },
    { label: 'Direct Serial', value: 'DIRECT_SERIAL' },
    { label: 'Direct USB', value: 'DIRECT_USB' },
  ]},
  { prop: 'serial_port', label: 'Port Serial', type: 'text', required: true },
  { prop: 'baudrate', label: 'Baudrate', type: 'number', required: true },
  { prop: 'mid', label: 'Merchant ID (MID)', type: 'text' },
  { prop: 'tid', label: 'Terminal ID (TID)', type: 'text' },
  { prop: 'encrypted_init_key', label: 'Init Key (Encrypted)', type: 'text' },
  { prop: 'is_active', label: 'Aktif', type: 'boolean' },
]

function openEmoneyReaderModal(row = null) {
  emoneyReaderEditing.value = !!row
  emoneyReaderForm.value = row ? { ...row } : {}
  emoneyReaderModalVisible.value = true
}

async function saveEmoneyReader(data) {
  submitting.value = true
  try {
    if (emoneyReaderEditing.value) {
      await readerCrud.update(data.id, data)
    } else {
      await readerCrud.create(data)
    }
    emoneyReaderModalVisible.value = false
    await loadEmoneyReaders()
    ElMessage.success('E-Money reader disimpan')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menyimpan')
  } finally {
    submitting.value = false
  }
}

function confirmDeleteEmoneyReader(row) {
  deleteTargetName.value = row.name
  deleteAction.value = () => deleteEmoneyReader(row.id)
  deleteDialogVisible.value = true
}

async function deleteEmoneyReader(id) {
  submitting.value = true
  try {
    await readerCrud.remove(id)
    deleteDialogVisible.value = false
    await loadEmoneyReaders()
    ElMessage.success('E-Money reader dihapus')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menghapus')
  } finally {
    submitting.value = false
  }
}

async function loadEmoneyReaders() {
  loadingEmoneyReaders.value = true
  try {
    emoneyReaders.value = await readerCrud.list()
  } catch (err) {
    ElMessage.error('Gagal memuat e-money readers')
  } finally {
    loadingEmoneyReaders.value = false
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Delete dialog & lifecycle
// ─────────────────────────────────────────────────────────────────────────────
const deleteDialogVisible = ref(false)
const deleteTargetName = ref('')
const deleteAction = ref(null)

function executeDelete() {
  if (deleteAction.value) deleteAction.value()
}

onMounted(() => {
  loadGates()
  loadPos()
  loadCameras()
  loadPrinters()
  loadEmoneyReaders()
})
</script>
