<template>
  <div>
    <h1>Notifikasi</h1>
    <p class="text-secondary mb-3">Pantau transaksi unresolved, alert, dan status settlement.</p>

    <el-tabs v-model="activeTab" type="border-card">
      <!-- Unresolved E-Money -->
      <el-tab-pane label="E-Money Unresolved" name="unresolved">
        <DataTable
          :data="unresolvedEmoney"
          :columns="unresolvedColumns"
          :loading="loadingUnresolved"
          :show-add="false"
          :show-edit="false"
          :show-delete="false"
        />
      </el-tab-pane>

      <!-- Active Transactions -->
      <el-tab-pane label="Transaksi Aktif" name="active">
        <DataTable
          :data="activeTransactions"
          :columns="activeTxColumns"
          :loading="loadingActive"
          :show-add="false"
          :show-edit="false"
          :show-delete="false"
        />
      </el-tab-pane>

      <!-- Recent Alerts -->
      <el-tab-pane label="Alert Terbaru" name="alerts">
        <DataTable
          :data="recentAlerts"
          :columns="alertColumns"
          :loading="loadingAlerts"
          :show-add="false"
          :show-edit="false"
          :show-delete="false"
        />
      </el-tab-pane>

      <!-- Settlement Status -->
      <el-tab-pane label="Settlement" name="settlement">
        <div class="mb-3">
          <el-button type="primary" @click="triggerSettlement" :loading="triggering">
            Generate & Upload
          </el-button>
        </div>
        <DataTable
          :data="settlements"
          :columns="settlementColumns"
          :loading="loadingSettlements"
          :show-add="false"
          :show-edit="false"
          :show-delete="false"
        />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
definePageMeta({
  middleware: 'auth',
})

const { fetchApi } = useApi()

const activeTab = ref('unresolved')
const loadingUnresolved = ref(false)
const loadingActive = ref(false)
const loadingAlerts = ref(false)
const loadingSettlements = ref(false)
const triggering = ref(false)
const settlements = ref([])

const settlementColumns = [
  { prop: 'filename', label: 'Filename', width: 300 },
  { prop: 'batch_date', label: 'Tanggal', width: 120 },
  { prop: 'batch_number', label: 'Batch', width: 80 },
  { prop: 'total_transactions', label: 'Transaksi', width: 100 },
  { prop: 'total_amount', label: 'Jumlah (Rp)', width: 130, formatter: (v) => v?.toLocaleString('id-ID') },
  { prop: 'status', label: 'Status', width: 120, type: 'enum' },
  { prop: 'created_at', label: 'Dibuat', width: 160, formatter: (v) => v ? new Date(v).toLocaleString('id-ID') : '-' },
]

// Unresolved E-Money
const unresolvedEmoney = ref([])
const unresolvedColumns = [
  { prop: 'barcode', label: 'Barcode', width: 140 },
  { prop: 'plate_number', label: 'Plat', width: 120 },
  { prop: 'card_number', label: 'No. Kartu', width: 150 },
  { prop: 'entry_time', label: 'Masuk', width: 160, formatter: (v) => v ? new Date(v).toLocaleString('id-ID') : '-' },
  { prop: 'payment_method', label: 'Metode', width: 110 },
  { prop: 'status', label: 'Status', width: 120, type: 'enum' },
  { prop: 'gate_in_name', label: 'Gate Masuk', width: 130 },
]

// Active Transactions
const activeTransactions = ref([])
const activeTxColumns = [
  { prop: 'barcode', label: 'Barcode', width: 140 },
  { prop: 'plate_number', label: 'Plat', width: 120 },
  { prop: 'card_number', label: 'No. Kartu', width: 150 },
  { prop: 'entry_time', label: 'Masuk', width: 160, formatter: (v) => v ? new Date(v).toLocaleString('id-ID') : '-' },
  { prop: 'vehicle_type_name', label: 'Jenis', width: 100 },
  { prop: 'gate_in_name', label: 'Gate Masuk', width: 130 },
]

// Recent Alerts (manual opens + abandoned)
const recentAlerts = ref([])
const alertColumns = [
  { prop: 'type', label: 'Tipe', width: 150, type: 'enum' },
  { prop: 'gate_id', label: 'Gate', width: 100 },
  { prop: 'message', label: 'Pesan' },
  { prop: 'timestamp', label: 'Waktu', width: 160, formatter: (v) => v ? new Date(v).toLocaleString('id-ID') : '-' },
]

// Load data
onMounted(() => {
  loadUnresolved()
  loadActive()
  loadAlerts()
  loadSettlements()
})

async function loadUnresolved() {
  loadingUnresolved.value = true
  try {
    // Get LOST_CONTACT transactions
    const lost = await fetchApi('/api/transactions?status=LOST_CONTACT&limit=50')
    unresolvedEmoney.value = lost || []
  } catch (err) {
    ElMessage.error('Gagal memuat e-money unresolved')
  } finally {
    loadingUnresolved.value = false
  }
}

async function loadActive() {
  loadingActive.value = true
  try {
    const active = await fetchApi('/api/transactions?status=ACTIVE&limit=50')
    activeTransactions.value = active || []
  } catch (err) {
    ElMessage.error('Gagal memuat transaksi aktif')
  } finally {
    loadingActive.value = false
  }
}

async function loadAlerts() {
  loadingAlerts.value = true
  try {
    const [manualOpens, abandoned] = await Promise.all([
      fetchApi('/api/manual-open-logs?limit=20'),
      fetchApi('/api/abandoned-vehicle-logs?limit=20'),
    ])

    const alerts = []

    for (const item of (manualOpens.items || [])) {
      alerts.push({
        type: 'BUKA MANUAL',
        gate_id: item.gate_id,
        message: item.reason,
        timestamp: item.created_at,
      })
    }

    for (const item of (abandoned.items || [])) {
      alerts.push({
        type: 'KENDARAAN DITINGGAL',
        gate_id: item.gate_out_id,
        message: `Resolusi: ${item.resolution_type}`,
        timestamp: item.created_at,
      })
    }

    // Sort by timestamp desc
    alerts.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    recentAlerts.value = alerts
  } catch (err) {
    ElMessage.error('Gagal memuat alert')
  } finally {
    loadingAlerts.value = false
  }
}

async function loadSettlements() {
  loadingSettlements.value = true
  try {
    const data = await fetchApi('/api/settlements?limit=50')
    settlements.value = data || []
  } catch (err) {
    ElMessage.error('Gagal memuat settlement')
  } finally {
    loadingSettlements.value = false
  }
}

async function triggerSettlement() {
  triggering.value = true
  try {
    const result = await fetchApi('/api/settlements/trigger', { method: 'POST' })
    ElMessage.success(`Settlement generated: ${result.files_generated} file(s), ${result.total_transactions} transaction(s)`)
    await loadSettlements()
  } catch (err) {
    ElMessage.error('Gagal trigger settlement')
  } finally {
    triggering.value = false
  }
}
</script>
