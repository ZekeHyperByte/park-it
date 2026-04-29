<template>
  <div>
    <h1>Laporan</h1>
    <p class="text-secondary mb-3">Ringkasan transaksi dan settlement e-money.</p>

    <!-- Date Range Filter -->
    <el-card class="mb-3">
      <el-button-group class="mb-2">
        <el-button @click="setToday">Hari Ini</el-button>
        <el-button @click="setThisWeek">Minggu Ini</el-button>
        <el-button @click="setThisMonth">Bulan Ini</el-button>
        <el-button @click="setLastMonth">Bulan Lalu</el-button>
      </el-button-group>
      <div class="filter-row">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="s/d"
          start-placeholder="Tanggal Mulai"
          end-placeholder="Tanggal Akhir"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          style="width: 320px"
        />
        <el-button type="primary" :loading="loading" @click="loadReports">
          <el-icon><Search /></el-icon> Tampilkan
        </el-button>
      </div>
    </el-card>

    <el-tabs v-model="activeTab" type="border-card">
      <!-- Summary Report -->
      <el-tab-pane label="Ringkasan" name="summary">
        <div v-if="summaryReport" class="stats-grid">
          <el-card class="stat-card">
            <div class="stat-label">Total Transaksi</div>
            <div class="stat-value">{{ summaryReport.total_transactions.toLocaleString() }}</div>
          </el-card>
          <el-card class="stat-card">
            <div class="stat-label">Total Pendapatan</div>
            <div class="stat-value">Rp {{ summaryReport.total_revenue.toLocaleString() }}</div>
          </el-card>
          <el-card class="stat-card">
            <div class="stat-label">Pendapatan Cash</div>
            <div class="stat-value">Rp {{ summaryReport.cash_revenue.toLocaleString() }}</div>
          </el-card>
          <el-card class="stat-card">
            <div class="stat-label">Pendapatan E-Money</div>
            <div class="stat-value">Rp {{ summaryReport.emoney_revenue.toLocaleString() }}</div>
          </el-card>
          <el-card class="stat-card">
            <div class="stat-label">Pendapatan RFID</div>
            <div class="stat-value">Rp {{ summaryReport.rfid_revenue.toLocaleString() }}</div>
          </el-card>
          <el-card class="stat-card">
            <div class="stat-label">Tarif Rata-rata</div>
            <div class="stat-value">Rp {{ Math.round(summaryReport.average_fee).toLocaleString() }}</div>
          </el-card>
          <el-card class="stat-card">
            <div class="stat-label">Transaksi Aktif</div>
            <div class="stat-value">{{ summaryReport.active_transactions.toLocaleString() }}</div>
          </el-card>
          <el-card class="stat-card">
            <div class="stat-label">Transaksi Selesai</div>
            <div class="stat-value">{{ summaryReport.completed_transactions.toLocaleString() }}</div>
          </el-card>
        </div>
        <el-empty v-else description="Pilih rentang tanggal untuk melihat laporan" />
        <el-divider />
        <el-button-group>
          <el-button @click="exportReport('csv')">Export CSV</el-button>
          <el-button @click="exportReport('xlsx')">Export Excel</el-button>
          <el-button @click="exportReport('pdf')">Export PDF</el-button>
        </el-button-group>
      </el-tab-pane>

      <!-- Shift Report -->
      <el-tab-pane label="Per Shift" name="shift">
        <div v-if="shiftReport" class="stats-grid">
          <el-card v-for="item in shiftReport.items" :key="`${item.shift_id}-${item.date}`" class="stat-card">
            <div class="stat-label">{{ item.shift_name }} - {{ item.date }}</div>
            <div class="stat-value">{{ item.total_transactions.toLocaleString() }} transaksi</div>
            <div class="stat-value">Rp {{ item.total_revenue.toLocaleString() }}</div>
            <div class="text-small text-secondary">Operator: {{ item.operator_name || '-' }}</div>
          </el-card>
        </div>
        <el-empty v-else description="Pilih rentang tanggal untuk melihat laporan" />
      </el-tab-pane>

      <!-- E-Money Report -->
      <el-tab-pane label="E-Money" name="emoney">
        <div v-if="emoneyReport" class="stats-grid">
          <el-card class="stat-card">
            <div class="stat-label">Transaksi E-Money</div>
            <div class="stat-value">{{ emoneyReport.total_emoney_transactions.toLocaleString() }}</div>
          </el-card>
          <el-card class="stat-card">
            <div class="stat-label">Total Deducted</div>
            <div class="stat-value">Rp {{ emoneyReport.total_deducted.toLocaleString() }}</div>
          </el-card>
          <el-card class="stat-card">
            <div class="stat-label">Berhasil</div>
            <div class="stat-value stat-success">{{ emoneyReport.success_count.toLocaleString() }}</div>
          </el-card>
          <el-card class="stat-card">
            <div class="stat-label">Gagal</div>
            <div class="stat-value stat-danger">{{ emoneyReport.failed_count.toLocaleString() }}</div>
          </el-card>
          <el-card class="stat-card">
            <div class="stat-label">Lost Contact</div>
            <div class="stat-value stat-warning">{{ emoneyReport.lost_contact_count.toLocaleString() }}</div>
          </el-card>
          <el-card class="stat-card">
            <div class="stat-label">Rata-rata Deduct</div>
            <div class="stat-value">Rp {{ Math.round(emoneyReport.average_deduct_amount).toLocaleString() }}</div>
          </el-card>
          <el-card class="stat-card">
            <div class="stat-label">Belum Settlement</div>
            <div class="stat-value">{{ emoneyReport.unsettled_count.toLocaleString() }}</div>
          </el-card>
          <el-card class="stat-card">
            <div class="stat-label">Sudah Settlement</div>
            <div class="stat-value">{{ emoneyReport.settled_count.toLocaleString() }}</div>
          </el-card>
        </div>
        <el-empty v-else description="Pilih rentang tanggal untuk melihat laporan" />
        <el-divider />
        <el-button-group>
          <el-button @click="exportReport('csv')">Export CSV</el-button>
          <el-button @click="exportReport('xlsx')">Export Excel</el-button>
          <el-button @click="exportReport('pdf')">Export PDF</el-button>
        </el-button-group>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { Search } from '@element-plus/icons-vue'

definePageMeta({
  middleware: 'auth',
})

const { fetchApi } = useApi()

const activeTab = ref('summary')

// Default date range: start of current month to today
const today = new Date()
const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1)
const dateRange = ref([
  firstDayOfMonth.toISOString().split('T')[0],
  today.toISOString().split('T')[0],
])

const loading = ref(false)
const summaryReport = ref(null)
const emoneyReport = ref(null)
const shiftReport = ref(null)

// Auto-load on mount with default range
onMounted(() => {
  loadReports()
})

async function loadReports() {
  if (!dateRange.value || dateRange.value.length !== 2) {
    ElMessage.warning('Pilih rentang tanggal terlebih dahulu')
    return
  }

  loading.value = true
  try {
    const [date_from, date_to] = dateRange.value
    const qs = new URLSearchParams({ date_from, date_to })

    const [summary, emoney, shift] = await Promise.all([
      fetchApi(`/api/reports/summary?${qs.toString()}`),
      fetchApi(`/api/reports/emoney?${qs.toString()}`),
      fetchApi(`/api/reports/shift?${qs.toString()}`),
    ])

    summaryReport.value = summary
    emoneyReport.value = emoney
    shiftReport.value = shift
  } catch (err) {
    ElMessage.error('Gagal memuat laporan')
  } finally {
    loading.value = false
  }
}

function setToday() {
  const today = new Date().toISOString().split('T')[0]
  dateRange.value = [today, today]
  loadReports()
}

function setThisWeek() {
  const now = new Date()
  const monday = new Date(now.setDate(now.getDate() - now.getDay() + 1))
  const sunday = new Date(now.setDate(monday.getDate() + 6))
  dateRange.value = [
    monday.toISOString().split('T')[0],
    sunday.toISOString().split('T')[0],
  ]
  loadReports()
}

function setThisMonth() {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), 1)
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0)
  dateRange.value = [
    start.toISOString().split('T')[0],
    end.toISOString().split('T')[0],
  ]
  loadReports()
}

function setLastMonth() {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth() - 1, 1)
  const end = new Date(now.getFullYear(), now.getMonth(), 0)
  dateRange.value = [
    start.toISOString().split('T')[0],
    end.toISOString().split('T')[0],
  ]
  loadReports()
}

async function exportReport(format) {
  if (!dateRange.value || dateRange.value.length !== 2) {
    ElMessage.warning('Pilih rentang tanggal terlebih dahulu')
    return
  }
  const [from, to] = dateRange.value
  const url = `/api/reports/summary/export?format=${format}&date_from=${from}&date_to=${to}`

  try {
    const response = await fetchApi(url, { responseType: 'blob' })
    const blob = new Blob([response.data])
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `EParking_Report_Summary_${from}_${to}.${format}`
    link.click()
    ElMessage.success(`Report exported as ${format.toUpperCase()}`)
  } catch (e) {
    ElMessage.error('Export failed')
  }
}
</script>

<style scoped>
.filter-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}

.stat-card {
  text-align: center;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.stat-success {
  color: #67c23a;
}

.stat-danger {
  color: #f56c6c;
}

.stat-warning {
  color: #e6a23c;
}
</style>
