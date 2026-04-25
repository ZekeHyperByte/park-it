<template>
  <div class="pos-page">
    <!-- Page header -->
    <el-row :gutter="16" class="mb-3">
      <el-col :span="16">
        <h1 class="pos-title">Point of Sale — Gate Out</h1>
        <p class="pos-subtitle">
          Gate: <strong>{{ selectedGate?.name || '—' }}</strong>
          &nbsp;|&nbsp; Status:
          <el-tag :type="wsStatusType" size="small">{{ wsStatusText }}</el-tag>
        </p>
      </el-col>
      <el-col :span="8" class="text-right">
        <el-select
          v-model="gateStore.selectedGateOutId"
          placeholder="Pilih Gate Out"
          style="width: 220px"
          @change="onGateChange"
        >
          <el-option
            v-for="g in websiteStore.activeGateOuts"
            :key="g.id"
            :label="g.name"
            :value="g.id"
          />
        </el-select>
      </el-col>
    </el-row>

    <!-- Main POS layout -->
    <el-row :gutter="16">
      <!-- Left: Transaction + Snapshot -->
      <el-col :span="14">
        <el-card class="pos-card" shadow="hover">
          <template #header>
            <span>Transaksi Aktif</span>
          </template>

          <div v-if="gateStore.currentTransaction" class="transaction-detail">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="Barcode">{{ gateStore.currentTransaction.barcode }}</el-descriptions-item>
              <el-descriptions-item label="Plat Nomor">{{ gateStore.currentTransaction.plate_number || '—' }}</el-descriptions-item>
              <el-descriptions-item label="Jenis">{{ gateStore.currentTransaction.vehicle_type }}</el-descriptions-item>
              <el-descriptions-item label="Waktu Masuk">{{ gateStore.currentTransaction.entry_time }}</el-descriptions-item>
              <el-descriptions-item label="Durasi">{{ gateStore.currentTransaction.duration }}</el-descriptions-item>
              <el-descriptions-item label="Tarif">
                <strong class="ep-red">Rp {{ formatNumber(gateStore.currentTransaction.tariff) }}</strong>
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <div v-else class="transaction-empty text-center p-4">
            <el-icon :size="48" color="#dcdfe6"><Ticket /></el-icon>
            <p class="mt-2" style="color: #909399;">Tidak ada transaksi aktif</p>
          </div>

          <!-- Snapshot preview -->
          <div v-if="gateStore.cameraSnapshot" class="snapshot-preview mt-3">
            <el-image
              :src="gateStore.cameraSnapshot"
              fit="cover"
              style="width: 100%; height: 240px; border-radius: 4px;"
            >
              <template #error>
                <div class="image-slot">
                  <el-icon><Picture /></el-icon>
                </div>
              </template>
            </el-image>
          </div>
        </el-card>
      </el-col>

      <!-- Right: Payment Methods -->
      <el-col :span="10">
        <el-card class="pos-card payment-panel" shadow="hover">
          <template #header>
            <span>Metode Pembayaran</span>
          </template>

          <!-- Payment timeout alert -->
          <el-alert
            v-if="gateStore.isTimeout"
            :title="gateStore.alertMessage || 'Waktu pembayaran habis'"
            type="warning"
            show-icon
            :closable="false"
            class="mb-3"
          />

          <!-- Cash Payment -->
          <div class="payment-method mb-3">
            <el-button
              type="primary"
              size="large"
              class="w-full payment-btn"
              :disabled="!gateStore.canPayCash"
              @click="openCashModal"
            >
              <el-icon class="mr-2"><Money /></el-icon>
              Bayar Tunai
            </el-button>
          </div>

          <!-- RFID Payment -->
          <div class="payment-method mb-3">
            <el-button
              type="success"
              size="large"
              class="w-full payment-btn"
              :disabled="!gateStore.canPayRfid"
              @click="startRfidPayment"
            >
              <el-icon class="mr-2"><Postcard /></el-icon>
              Bayar RFID Member
            </el-button>
          </div>

          <!-- E-Money Payment -->
          <div class="payment-method">
            <el-button
              type="warning"
              size="large"
              class="w-full payment-btn"
              :disabled="!gateStore.canPayEmoney"
              @click="startEmoneyPayment"
            >
              <el-icon class="mr-2"><CreditCard /></el-icon>
              Bayar E-Money
            </el-button>
          </div>

          <!-- E-Money status panel -->
          <EmoneyPaymentStatus v-if="gateStore.emoneyPaymentState !== 'IDLE'" class="mt-3" />
        </el-card>
      </el-col>
    </el-row>

    <!-- Cash Payment Modal -->
    <el-dialog
      v-model="cashModalVisible"
      title="Pembayaran Tunai"
      width="400px"
      :close-on-click-modal="false"
    >
      <div v-if="gateStore.currentTransaction">
        <p class="mb-2">Total yang harus dibayar:</p>
        <h2 class="text-center ep-red mb-3">
          Rp {{ formatNumber(gateStore.currentTransaction.tariff) }}
        </h2>
        <el-form label-position="top">
          <el-form-item label="Uang Diterima">
            <el-input-number
              v-model="cashReceived"
              :min="0"
              :step="1000"
              style="width: 100%"
              size="large"
            />
          </el-form-item>
          <el-form-item label="Kembalian">
            <el-input
              :model-value="formatNumber(changeAmount)"
              readonly
              size="large"
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="cashModalVisible = false">Batal</el-button>
        <el-button type="primary" @click="confirmCashPayment">Konfirmasi</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { Ticket, Picture, Money, Postcard, CreditCard } from '@element-plus/icons-vue'

definePageMeta({
  middleware: 'auth',
})

const authStore = useAuthStore()
const websiteStore = useWebsiteStore()
const gateStore = useGateStore()
const { $ws } = useNuxtApp()

// Local state
const cashModalVisible = ref(false)
const cashReceived = ref(0)
let unsubscribeWs = null

// Computed
const selectedGate = computed(() =>
  websiteStore.activeGateOuts.find((g) => g.id === gateStore.selectedGateOutId)
)

const wsStatusText = computed(() => {
  if (!gateStore.selectedGateOutId) return 'No Gate'
  return $ws.isConnected(`gate-out-${gateStore.selectedGateOutId}`) ? 'Connected' : 'Disconnected'
})

const wsStatusType = computed(() => {
  if (!gateStore.selectedGateOutId) return 'info'
  return $ws.isConnected(`gate-out-${gateStore.selectedGateOutId}`) ? 'success' : 'danger'
})

const changeAmount = computed(() => {
  const tariff = gateStore.currentTransaction?.tariff || 0
  return Math.max(0, cashReceived.value - tariff)
})

// Methods
function formatNumber(n) {
  if (n === undefined || n === null) return '0'
  return Number(n).toLocaleString('id-ID')
}

function onGateChange(gateId) {
  // Unsubscribe from previous gate
  if (unsubscribeWs) {
    unsubscribeWs()
    unsubscribeWs = null
  }

  gateStore.clearTransaction()

  if (!gateId) return

  const gate = websiteStore.activeGateOuts.find((g) => g.id === gateId)
  if (!gate) return

  const gateCode = gate.code || `gate-out-${gateId}`

  // Subscribe to WebSocket for this gate
  unsubscribeWs = $ws.on(gateCode, (event) => {
    gateStore.handleWsEvent(event)
  })

  gateStore.setWsConnected($ws.isConnected(gateCode))
}

function openCashModal() {
  cashReceived.value = gateStore.currentTransaction?.tariff || 0
  cashModalVisible.value = true
}

async function confirmCashPayment() {
  try {
    const { fetchApi } = useApi()
    await fetchApi('/api/payments/cash', {
      method: 'POST',
      body: JSON.stringify({
        transaction_id: gateStore.currentTransaction?.id,
        amount: gateStore.currentTransaction?.tariff,
        received: cashReceived.value,
      }),
    })
    ElMessage.success('Pembayaran tunai berhasil')
    cashModalVisible.value = false
    gateStore.clearTransaction()
  } catch (err) {
    ElMessage.error(err.message || 'Pembayaran gagal')
  }
}

function startRfidPayment() {
  ElMessage.info('Menunggu kartu RFID...')
}

function startEmoneyPayment() {
  gateStore.setEmoneyState('WAITING_CARD')
  ElMessage.info('Menunggu tap kartu e-money...')
}

// Lifecycle
onMounted(async () => {
  await websiteStore.loadAll()
  if (websiteStore.activeGateOuts.length > 0 && !gateStore.selectedGateOutId) {
    gateStore.setSelectedGateOutId(websiteStore.activeGateOuts[0].id)
    onGateChange(websiteStore.activeGateOuts[0].id)
  }
})

onUnmounted(() => {
  if (unsubscribeWs) {
    unsubscribeWs()
  }
})
</script>

<style scoped>
.pos-page {
  max-width: 1400px;
  margin: 0 auto;
}

.pos-title {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
}

.pos-subtitle {
  margin: 4px 0 0;
  font-size: 14px;
  color: #606266;
}

.pos-card {
  min-height: 400px;
}

.payment-panel {
  background: #fafafa;
}

.payment-btn {
  height: 56px;
  font-size: 16px;
  font-weight: 500;
}

.transaction-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.snapshot-preview {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
}

.image-slot {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  background: #f5f7fa;
  color: #909399;
}
</style>
