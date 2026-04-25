<template>
  <div>
    <h1>Perangkat</h1>
    <p class="text-secondary mb-3">Manajemen gate masuk, gate keluar, dan e-money reader.</p>

    <el-tabs v-model="activeTab" type="border-card">
      <!-- Gate In -->
      <el-tab-pane label="Gate Masuk" name="gate-in">
        <DataTable
          :data="gateIns"
          :columns="gateInColumns"
          :loading="loadingGateIns"
          @add="openGateInModal()"
          @edit="openGateInModal"
          @delete="confirmDeleteGateIn"
        />
      </el-tab-pane>

      <!-- Gate Out -->
      <el-tab-pane label="Gate Keluar" name="gate-out">
        <DataTable
          :data="gateOuts"
          :columns="gateOutColumns"
          :loading="loadingGateOuts"
          @add="openGateOutModal()"
          @edit="openGateOutModal"
          @delete="confirmDeleteGateOut"
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

    <!-- Gate In Modal -->
    <CrudModal
      v-model="gateInModalVisible"
      :title="gateInEditing ? 'Edit Gate Masuk' : 'Tambah Gate Masuk'"
      :fields="gateInFields"
      :initial-data="gateInForm"
      :submitting="submitting"
      @submit="saveGateIn"
    />

    <!-- Gate Out Modal -->
    <CrudModal
      v-model="gateOutModalVisible"
      :title="gateOutEditing ? 'Edit Gate Keluar' : 'Tambah Gate Keluar'"
      :fields="gateOutFields"
      :initial-data="gateOutForm"
      :submitting="submitting"
      @submit="saveGateOut"
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
const gateInCrud = useCrud('/api/gates/in')
const gateOutCrud = useCrud('/api/gates/out')
const readerCrud = useCrud('/api/emoney-readers')

const activeTab = ref('gate-in')
const submitting = ref(false)

// Gate In
const gateIns = ref([])
const loadingGateIns = ref(false)
const gateInModalVisible = ref(false)
const gateInEditing = ref(false)
const gateInForm = ref({})
const gateInColumns = [
  { prop: 'name', label: 'Nama', sortable: true },
  { prop: 'code', label: 'Kode', width: 120, sortable: true },
  { prop: 'gate_mode', label: 'Mode', width: 120, type: 'enum' },
  { prop: 'protocol', label: 'Protokol', width: 120, type: 'enum' },
  { prop: 'controller_host', label: 'Host', width: 150 },
  { prop: 'is_active', label: 'Aktif', type: 'boolean', width: 80 },
]
const gateInFields = [
  { prop: 'name', label: 'Nama', type: 'text', required: true },
  { prop: 'code', label: 'Kode', type: 'text', required: true },
  { prop: 'gate_mode', label: 'Mode Gate', type: 'select', required: true, options: [
    { label: 'Cash', value: 'CASH' },
    { label: 'RFID', value: 'RFID' },
    { label: 'E-Money', value: 'EMONEY' },
  ]},
  { prop: 'protocol', label: 'Protokol', type: 'select', required: true, options: [
    { label: 'Compass', value: 'compass' },
    { label: 'ENET', value: 'enet' },
    { label: 'Serial', value: 'serial' },
  ]},
  { prop: 'controller_host', label: 'Host Controller', type: 'text' },
  { prop: 'controller_port', label: 'Port Controller', type: 'number' },
  { prop: 'emoney_minimum_balance', label: 'Min. Saldo E-Money', type: 'number' },
  { prop: 'print_decision_timeout_seconds', label: 'Timeout Cetak (detik)', type: 'number' },
  { prop: 'has_close_sensor', label: 'Sensor Tutup', type: 'boolean' },
  { prop: 'relay_mode', label: 'Mode Relay', type: 'select', options: [
    { label: 'Single', value: 'SINGLE' },
    { label: 'Dual', value: 'DUAL' },
  ]},
  { prop: 'printer_type', label: 'Tipe Printer', type: 'select', options: [
    { label: 'Controller Passthrough', value: 'CONTROLLER_PASSTHROUGH' },
    { label: 'Network', value: 'NETWORK' },
    { label: 'Serial', value: 'SERIAL' },
  ]},
  { prop: 'printer_ip_address', label: 'IP Printer', type: 'text' },
  { prop: 'camera_url', label: 'URL Kamera', type: 'text' },
  { prop: 'is_active', label: 'Aktif', type: 'boolean' },
]

// Gate Out
const gateOuts = ref([])
const loadingGateOuts = ref(false)
const gateOutModalVisible = ref(false)
const gateOutEditing = ref(false)
const gateOutForm = ref({})
const gateOutColumns = [
  { prop: 'name', label: 'Nama', sortable: true },
  { prop: 'code', label: 'Kode', width: 120, sortable: true },
  { prop: 'protocol', label: 'Protokol', width: 120, type: 'enum' },
  { prop: 'controller_host', label: 'Host', width: 150 },
  { prop: 'payment_timeout_seconds', label: 'Timeout (detik)', width: 130 },
  { prop: 'is_active', label: 'Aktif', type: 'boolean', width: 80 },
]
const gateOutFields = [
  { prop: 'name', label: 'Nama', type: 'text', required: true },
  { prop: 'code', label: 'Kode', type: 'text', required: true },
  { prop: 'protocol', label: 'Protokol', type: 'select', required: true, options: [
    { label: 'Compass', value: 'compass' },
    { label: 'ENET', value: 'enet' },
    { label: 'Serial', value: 'serial' },
  ]},
  { prop: 'controller_host', label: 'Host Controller', type: 'text' },
  { prop: 'controller_port', label: 'Port Controller', type: 'number' },
  { prop: 'payment_timeout_seconds', label: 'Timeout Pembayaran (detik)', type: 'number' },
  { prop: 'has_close_sensor', label: 'Sensor Tutup', type: 'boolean' },
  { prop: 'relay_mode', label: 'Mode Relay', type: 'select', options: [
    { label: 'Single', value: 'SINGLE' },
    { label: 'Dual', value: 'DUAL' },
  ]},
  { prop: 'printer_type', label: 'Tipe Printer', type: 'select', options: [
    { label: 'Controller Passthrough', value: 'CONTROLLER_PASSTHROUGH' },
    { label: 'Network', value: 'NETWORK' },
    { label: 'Serial', value: 'SERIAL' },
  ]},
  { prop: 'printer_ip_address', label: 'IP Printer', type: 'text' },
  { prop: 'camera_url', label: 'URL Kamera', type: 'text' },
  { prop: 'is_active', label: 'Aktif', type: 'boolean' },
]

// E-Money Readers
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

// Delete dialog
const deleteDialogVisible = ref(false)
const deleteTargetName = ref('')
const deleteAction = ref(null)

// Load data
onMounted(() => {
  loadGateIns()
  loadGateOuts()
  loadEmoneyReaders()
})

// Gate In
async function loadGateIns() {
  loadingGateIns.value = true
  try {
    gateIns.value = await gateInCrud.list()
  } catch (err) {
    ElMessage.error('Gagal memuat gate masuk')
  } finally {
    loadingGateIns.value = false
  }
}

function openGateInModal(row = null) {
  gateInEditing.value = !!row
  gateInForm.value = row ? { ...row } : {}
  gateInModalVisible.value = true
}

async function saveGateIn(data) {
  submitting.value = true
  try {
    if (gateInEditing.value) {
      await gateInCrud.update(data.id, data)
    } else {
      await gateInCrud.create(data)
    }
    gateInModalVisible.value = false
    await loadGateIns()
    ElMessage.success('Gate masuk disimpan')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menyimpan')
  } finally {
    submitting.value = false
  }
}

function confirmDeleteGateIn(row) {
  deleteTargetName.value = row.name
  deleteAction.value = () => deleteGateIn(row.id)
  deleteDialogVisible.value = true
}

async function deleteGateIn(id) {
  submitting.value = true
  try {
    await gateInCrud.remove(id)
    deleteDialogVisible.value = false
    await loadGateIns()
    ElMessage.success('Gate masuk dihapus')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menghapus')
  } finally {
    submitting.value = false
  }
}

// Gate Out
async function loadGateOuts() {
  loadingGateOuts.value = true
  try {
    gateOuts.value = await gateOutCrud.list()
  } catch (err) {
    ElMessage.error('Gagal memuat gate keluar')
  } finally {
    loadingGateOuts.value = false
  }
}

function openGateOutModal(row = null) {
  gateOutEditing.value = !!row
  gateOutForm.value = row ? { ...row } : {}
  gateOutModalVisible.value = true
}

async function saveGateOut(data) {
  submitting.value = true
  try {
    if (gateOutEditing.value) {
      await gateOutCrud.update(data.id, data)
    } else {
      await gateOutCrud.create(data)
    }
    gateOutModalVisible.value = false
    await loadGateOuts()
    ElMessage.success('Gate keluar disimpan')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menyimpan')
  } finally {
    submitting.value = false
  }
}

function confirmDeleteGateOut(row) {
  deleteTargetName.value = row.name
  deleteAction.value = () => deleteGateOut(row.id)
  deleteDialogVisible.value = true
}

async function deleteGateOut(id) {
  submitting.value = true
  try {
    await gateOutCrud.remove(id)
    deleteDialogVisible.value = false
    await loadGateOuts()
    ElMessage.success('Gate keluar dihapus')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menghapus')
  } finally {
    submitting.value = false
  }
}

// E-Money Readers
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

// Generic delete execution
function executeDelete() {
  if (deleteAction.value) deleteAction.value()
}
</script>
