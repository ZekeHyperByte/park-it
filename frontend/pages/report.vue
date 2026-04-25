<template>
  <div>
    <h1>Laporan</h1>
    <p class="text-secondary mb-3">Ringkasan transaksi dan settlement e-money.</p>

    <!-- Date Range Filter -->
    <el-card class="mb-3">
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
const dateRange = ref(null)
const loading = ref(false)
const summaryReport = ref(null)
const emoneyReport = ref(null)

async function loadReports() {
  if (!dateRange.value || dateRange.value.length !== 2) {
    ElMessage.warning('Pilih rentang tanggal terlebih dahulu')
    return
  }

  loading.value = true
  try {
    const [date_from, date_to] = dateRange.value
    const qs = new URLSearchParams({ date_from, date_to })

    const [summary, emoney] = await Promise.all([
      fetchApi(`/api/reports/summary?${qs.toString()}`),
      fetchApi(`/api/reports/emoney?${qs.toString()}`),
    ])

    summaryReport.value = summary
    emoneyReport.value = emoney
  } catch (err) {
    ElMessage.error('Gagal memuat laporan')
  } finally {
    loading.value = false
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
