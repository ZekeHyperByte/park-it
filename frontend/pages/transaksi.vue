<template>
  <div>
    <h1>Transaksi</h1>
    <p class="text-secondary mb-3">Riwayat transaksi parkir dan log peristiwa.</p>

    <el-tabs v-model="activeTab" type="border-card">
      <!-- Transactions -->
      <el-tab-pane label="Transaksi Parkir" name="transactions">
        <div class="filter-bar mb-3">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="s/d"
            start-placeholder="Tanggal Mulai"
            end-placeholder="Tanggal Akhir"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 300px"
            @change="loadTransactions"
          />
          <el-select
            v-model="statusFilter"
            placeholder="Status"
            clearable
            style="width: 150px; margin-left: 10px"
            @change="loadTransactions"
          >
            <el-option label="Aktif" value="ACTIVE" />
            <el-option label="Selesai" value="COMPLETED" />
            <el-option label="Lost Contact" value="LOST_CONTACT" />
          </el-select>
        </div>
        <DataTable
          :data="transactions"
          :columns="transactionColumns"
          :loading="loadingTransactions"
          :show-add="false"
          :show-edit="false"
          :show-delete="false"
          server-pagination
          :total-items="transactionTotal"
          @page-change="handleTransactionPageChange"
          @size-change="handleTransactionSizeChange"
        />
      </el-tab-pane>

      <!-- Manual Open Logs -->
      <el-tab-pane label="Buka Manual" name="manual-opens">
        <DataTable
          :data="manualOpens"
          :columns="manualOpenColumns"
          :loading="loadingManualOpens"
          :show-add="false"
          :show-edit="false"
          :show-delete="false"
        />
      </el-tab-pane>

      <!-- Abandoned Vehicles -->
      <el-tab-pane label="Kendaraan Ditinggal" name="abandoned">
        <DataTable
          :data="abandonedVehicles"
          :columns="abandonedColumns"
          :loading="loadingAbandoned"
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

const activeTab = ref('transactions')
const loadingTransactions = ref(false)
const loadingManualOpens = ref(false)
const loadingAbandoned = ref(false)

// Filters
const dateRange = ref(null)
const statusFilter = ref('')

// Transactions
const transactions = ref([])
const transactionTotal = ref(0)
const transactionPage = ref(1)
const transactionPageSize = ref(20)
const transactionColumns = [
  { prop: 'barcode', label: 'Barcode', width: 140, sortable: true },
  { prop: 'plate_number', label: 'Plat', width: 120, sortable: true },
  { prop: 'vehicle_type_name', label: 'Jenis', width: 100 },
  { prop: 'gate_in_name', label: 'Gate Masuk', width: 130 },
  { prop: 'gate_out_name', label: 'Gate Keluar', width: 130 },
  { prop: 'entry_time', label: 'Masuk', width: 160, formatter: (v) => v ? new Date(v).toLocaleString('id-ID') : '-' },
  { prop: 'exit_time', label: 'Keluar', width: 160, formatter: (v) => v ? new Date(v).toLocaleString('id-ID') : '-' },
  { prop: 'duration_minutes', label: 'Durasi (menit)', width: 120 },
  { prop: 'payment_method', label: 'Metode', width: 110 },
  { prop: 'fee', label: 'Tarif', width: 120, formatter: (v) => v ? `Rp ${v.toLocaleString()}` : '-' },
  { prop: 'status', label: 'Status', width: 120, type: 'enum' },
]

// Manual Open Logs
const manualOpens = ref([])
const manualOpenColumns = [
  { prop: 'gate_id', label: 'Gate ID', width: 100 },
  { prop: 'gate_type', label: 'Tipe', width: 100 },
  { prop: 'reason', label: 'Alasan' },
  { prop: 'notes', label: 'Catatan' },
]

// Abandoned Vehicles
const abandonedVehicles = ref([])
const abandonedColumns = [
  { prop: 'gate_out_id', label: 'Gate Out', width: 100 },
  { prop: 'waiting_seconds', label: 'Tunggu (detik)', width: 130, sortable: true },
  { prop: 'resolution_type', label: 'Resolusi', width: 150, type: 'enum' },
  { prop: 'notes', label: 'Catatan' },
]

// Load data
onMounted(() => {
  loadTransactions()
  loadManualOpens()
  loadAbandoned()
})

async function loadTransactions() {
  loadingTransactions.value = true
  try {
    const params = {
      skip: (transactionPage.value - 1) * transactionPageSize.value,
      limit: transactionPageSize.value,
    }
    if (dateRange.value && dateRange.value.length === 2) {
      params.date_from = dateRange.value[0]
      params.date_to = dateRange.value[1]
    }
    if (statusFilter.value) {
      params.status = statusFilter.value
    }
    const qs = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') qs.append(k, v)
    }
    const result = await fetchApi(`/api/transactions?${qs.toString()}`)
    transactions.value = result
    // Note: API returns list only; for true server pagination we need total count.
    // Using result length as fallback until API provides total.
    transactionTotal.value = result.length === transactionPageSize.value
      ? (transactionPage.value * transactionPageSize.value) + 1
      : (transactionPage.value - 1) * transactionPageSize.value + result.length
  } catch (err) {
    ElMessage.error('Gagal memuat transaksi')
  } finally {
    loadingTransactions.value = false
  }
}

function handleTransactionPageChange(page, size) {
  transactionPage.value = page
  transactionPageSize.value = size
  loadTransactions()
}

function handleTransactionSizeChange(page, size) {
  transactionPage.value = page
  transactionPageSize.value = size
  loadTransactions()
}

async function loadManualOpens() {
  loadingManualOpens.value = true
  try {
    const result = await fetchApi('/api/manual-open-logs')
    manualOpens.value = result.items || []
  } catch (err) {
    ElMessage.error('Gagal memuat log buka manual')
  } finally {
    loadingManualOpens.value = false
  }
}

async function loadAbandoned() {
  loadingAbandoned.value = true
  try {
    const result = await fetchApi('/api/abandoned-vehicle-logs')
    abandonedVehicles.value = result.items || []
  } catch (err) {
    ElMessage.error('Gagal memuat kendaraan ditinggal')
  } finally {
    loadingAbandoned.value = false
  }
}
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
}
</style>
