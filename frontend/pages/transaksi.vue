<template>
  <div>
    <h1 class="text-xl font-semibold text-foreground">Transaksi</h1>
    <p class="mb-4 text-sm text-muted-foreground">Riwayat transaksi parkir dan log peristiwa.</p>

    <!-- Tabs (Tailwind-styled) -->
    <div class="mb-4 flex gap-1 border-b border-border">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="[
          'px-4 py-2 text-sm font-medium transition-colors -mb-px',
          activeTab === tab.key
            ? 'border-b-2 border-primary text-primary'
            : 'text-muted-foreground hover:text-foreground',
        ]"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Transactions tab -->
    <div v-if="activeTab === 'transactions'">
      <div class="mb-4 flex items-center gap-3">
        <input
          v-model="dateFrom"
          type="date"
          class="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground"
        />
        <span class="text-muted-foreground">s/d</span>
        <input
          v-model="dateTo"
          type="date"
          class="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground"
        />
        <select
          v-model="statusFilter"
          class="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground"
        >
          <option value="">Semua Status</option>
          <option value="ACTIVE">Aktif</option>
          <option value="COMPLETED">Selesai</option>
          <option value="LOST_CONTACT">Lost Contact</option>
        </select>
        <Button size="sm" @click="loadTransactions">Filter</Button>
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
    </div>

    <!-- Manual Opens tab -->
    <div v-if="activeTab === 'manual-opens'">
      <DataTable
        :data="manualOpens"
        :columns="manualOpenColumns"
        :loading="loadingManualOpens"
        :show-add="false"
        :show-edit="false"
        :show-delete="false"
      />
    </div>

    <!-- Abandoned tab -->
    <div v-if="activeTab === 'abandoned'">
      <DataTable
        :data="abandonedVehicles"
        :columns="abandonedColumns"
        :loading="loadingAbandoned"
        :show-add="false"
        :show-edit="false"
        :show-delete="false"
      />
    </div>
  </div>
</template>

<script setup>
import { Button } from '~/components/ui/button'

definePageMeta({ middleware: 'auth' })

const { fetchApi } = useApi()

const tabs = [
  { key: 'transactions', label: 'Transaksi Parkir' },
  { key: 'manual-opens', label: 'Buka Manual' },
  { key: 'abandoned', label: 'Kendaraan Ditinggal' },
]

const activeTab = ref('transactions')
const loadingTransactions = ref(false)
const loadingManualOpens = ref(false)
const loadingAbandoned = ref(false)

const dateFrom = ref('')
const dateTo = ref('')
const statusFilter = ref('')

// Set default date range
const today = new Date()
const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
dateFrom.value = firstDay.toISOString().split('T')[0]
dateTo.value = today.toISOString().split('T')[0]

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

const manualOpens = ref([])
const manualOpenColumns = [
  { prop: 'gate_id', label: 'Gate ID', width: 100 },
  { prop: 'gate_type', label: 'Tipe', width: 100 },
  { prop: 'reason', label: 'Alasan' },
  { prop: 'notes', label: 'Catatan' },
]

const abandonedVehicles = ref([])
const abandonedColumns = [
  { prop: 'gate_out_id', label: 'Gate Out', width: 100 },
  { prop: 'waiting_seconds', label: 'Tunggu (detik)', width: 130, sortable: true },
  { prop: 'resolution_type', label: 'Resolusi', width: 150, type: 'enum' },
  { prop: 'notes', label: 'Catatan' },
]

// Lazy-load tabs: fetch only on first activation, cache thereafter.
const _loaded = reactive({ transactions: false, 'manual-opens': false, abandoned: false })

watch(
  activeTab,
  (tab) => {
    if (_loaded[tab]) return
    if (tab === 'transactions') loadTransactions()
    else if (tab === 'manual-opens') loadManualOpens()
    else if (tab === 'abandoned') loadAbandoned()
    _loaded[tab] = true
  },
  { immediate: true },
)

async function loadTransactions() {
  loadingTransactions.value = true
  try {
    const params = {
      skip: (transactionPage.value - 1) * transactionPageSize.value,
      limit: transactionPageSize.value,
    }
    if (dateFrom.value) params.date_from = dateFrom.value
    if (dateTo.value) params.date_to = dateTo.value
    if (statusFilter.value) params.status = statusFilter.value
    const qs = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') qs.append(k, v)
    }
    // Backend returns {items, total, skip, limit} — see
    // api/app/routes/transactions.py::TransactionListResponse.
    const result = await fetchApi(`/api/transactions?${qs.toString()}`)
    transactions.value = result.items ?? []
    transactionTotal.value = typeof result.total === 'number' ? result.total : transactions.value.length
  } catch (err) {
    console.error('Gagal memuat transaksi:', err)
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
    console.error('Gagal memuat log buka manual:', err)
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
    console.error('Gagal memuat kendaraan ditinggal:', err)
  } finally {
    loadingAbandoned.value = false
  }
}
</script>
