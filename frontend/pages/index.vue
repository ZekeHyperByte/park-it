<template>
  <div class="pos-page">
    <!-- Page header -->
    <el-row :gutter="16" class="mb-3">
      <el-col :span="16">
        <h1 class="pos-title">Point of Sale — Gate Out</h1>
        <p class="pos-subtitle">
          Gate: <strong>{{ selectedGate?.name || '—' }}</strong>
          &nbsp;|&nbsp; Gate WS:
          <el-tag :type="wsStatusType" size="small">{{ wsStatusText }}</el-tag>
          &nbsp;|&nbsp; Booth:
          <el-tag :type="gateStore.boothConnected ? 'success' : 'danger'" size="small">
            {{ gateStore.boothConnected ? 'Connected' : 'Disconnected' }}
          </el-tag>
        </p>
      </el-col>
      <el-col :span="8" class="text-right">
        <el-select
          v-if="gateSelectorVisible"
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
        <el-tag v-else type="info" size="large">
          {{ selectedGate?.name || '—' }}
        </el-tag>
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

          <!-- Barcode lookup -->
          <div class="mb-3">
            <el-input
              v-model="barcodeInput"
              placeholder="Scan barcode atau masukkan plat nomor..."
              clearable
              @keyup.enter="onBarcodeLookup"
            >
              <template #append>
                <el-button @click="onBarcodeLookup">
                  <el-icon><Search /></el-icon>
                </el-button>
              </template>
            </el-input>
          </div>

          <div v-if="gateStore.currentTransaction" class="transaction-detail">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="Barcode">{{ gateStore.currentTransaction.barcode || '—' }}</el-descriptions-item>
              <el-descriptions-item label="Plat Nomor">{{ gateStore.currentTransaction.plate_number || '—' }}</el-descriptions-item>
              <el-descriptions-item label="Jenis">{{ vehicleTypeName }}</el-descriptions-item>
              <el-descriptions-item label="Waktu Masuk">{{ formatDateTime(gateStore.currentTransaction.entry_time) }}</el-descriptions-item>
              <el-descriptions-item label="Durasi">{{ durationText }}</el-descriptions-item>
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
              :disabled="!gateStore.canPayCash || gateStore.isLoading"
              :loading="gateStore.isLoading && activeMethod === 'cash'"
              @click="openCashModal"
            >
              <el-icon class="mr-2"><Money /></el-icon>
              Bayar Tunai (F1)
            </el-button>
          </div>

          <!-- RFID Payment -->
          <div class="payment-method mb-3">
            <el-button
              type="success"
              size="large"
              class="w-full payment-btn"
              :disabled="!gateStore.canPayRfid || gateStore.isLoading"
              :loading="gateStore.isLoading && activeMethod === 'rfid'"
              @click="startRfidPayment"
            >
              <el-icon class="mr-2"><Postcard /></el-icon>
              Bayar RFID Member (F2)
            </el-button>
          </div>

          <!-- E-Money Payment -->
          <div class="payment-method">
            <el-button
              type="warning"
              size="large"
              class="w-full payment-btn"
              :disabled="!gateStore.canPayEmoney || gateStore.isLoading"
              :loading="gateStore.isLoading && activeMethod === 'emoney'"
              @click="startEmoneyPayment"
            >
              <el-icon class="mr-2"><CreditCard /></el-icon>
              Bayar E-Money (F3)
            </el-button>
          </div>

          <!-- E-Money status panel -->
          <EmoneyPaymentStatus v-if="gateStore.emoneyPaymentState !== 'IDLE'" class="mt-3" />

          <!-- Open Gate button — shown after cash payment confirmation -->
          <el-card v-if="gateStore.awaitingGateOpen" class="open-gate-card mt-3" shadow="never">
            <div class="text-center">
              <p style="color: #e6a23c; font-weight: 500; margin-bottom: 12px;">
                Pembayaran selesai. Struk sedang dicetak.
              </p>
              <el-button
                type="success"
                size="large"
                class="open-gate-btn"
                :loading="gateStore.isLoading"
                @click="openGateAction"
              >
                <el-icon class="mr-2"><Unlock /></el-icon>
                Buka Palang & Cetak Struk
              </el-button>
              <p class="mt-2" style="color: #909399; font-size: 13px;">
                Tekan <kbd>Space</kbd> untuk membuka palang
              </p>
            </div>
          </el-card>
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
              @keyup.enter="confirmCashPayment"
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
        <el-button type="primary" :loading="gateStore.isLoading" @click="confirmCashPayment">
          Konfirmasi (Enter)
        </el-button>
      </template>
    </el-dialog>

    <!-- RFID Card Input Modal -->
    <el-dialog
      v-model="rfidModalVisible"
      title="Bayar RFID Member"
      width="400px"
      :close-on-click-modal="false"
    >
      <p class="mb-2">Tempelkan atau masukkan nomor kartu member:</p>
      <el-input
        v-model="rfidCardNumber"
        placeholder="Nomor kartu RFID"
        size="large"
        clearable
        @keyup.enter="confirmRfidPayment"
      />
      <template #footer>
        <el-button @click="rfidModalVisible = false">Batal</el-button>
        <el-button type="success" :loading="gateStore.isLoading" @click="confirmRfidPayment">
          Konfirmasi
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { Ticket, Picture, Money, Postcard, CreditCard, Search, Unlock } from '@element-plus/icons-vue'

definePageMeta({
  middleware: 'auth',
})

const authStore = useAuthStore()
const websiteStore = useWebsiteStore()
const gateStore = useGateStore()
const { $ws } = useNuxtApp()
const { fetchApi } = useApi()

// Local state
const cashModalVisible = ref(false)
const cashReceived = ref(0)
const rfidModalVisible = ref(false)
const rfidCardNumber = ref('')
const barcodeInput = ref('')
const activeMethod = ref(null)
let unsubscribeWs = null
let boothWs = null
let boothWsReconnectTimer = null

// Booth auto-detection
const currentPos = ref(null)
const isAdmin = computed(() => authStore.user?.role === 'admin')
const gateSelectorVisible = computed(() => isAdmin.value || !currentPos.value?.default_gate_id)

// Computed
const selectedGate = computed(() =>
  websiteStore.activeGateOuts.find((g) => g.id === gateStore.selectedGateOutId)
)

const wsStatusText = computed(() => {
  if (!gateStore.selectedGateOutId) return 'No Gate'
  const gateCode = selectedGate.value?.code || `gate-out-${gateStore.selectedGateOutId}`
  return $ws.isConnected(gateCode) ? 'Connected' : 'Disconnected'
})

const wsStatusType = computed(() => {
  if (!gateStore.selectedGateOutId) return 'info'
  const gateCode = selectedGate.value?.code || `gate-out-${gateStore.selectedGateOutId}`
  return $ws.isConnected(gateCode) ? 'success' : 'danger'
})

const changeAmount = computed(() => {
  const tariff = gateStore.currentTransaction?.tariff || 0
  return Math.max(0, cashReceived.value - tariff)
})

const vehicleTypeName = computed(() => {
  const vtId = gateStore.currentTransaction?.vehicle_type_id
  if (!vtId) return '—'
  const vt = websiteStore.vehicleTypes?.find((v) => v.id === vtId)
  return vt?.name || '—'
})

const durationText = computed(() => {
  const entryTime = gateStore.currentTransaction?.entry_time
  if (!entryTime) return '—'
  const entry = new Date(entryTime)
  const now = new Date()
  const diffMs = now - entry
  const diffH = Math.floor(diffMs / 3600000)
  const diffM = Math.floor((diffMs % 3600000) / 60000)
  return `${diffH}j ${diffM}m`
})

// Methods
function formatNumber(n) {
  if (n === undefined || n === null) return '0'
  return Number(n).toLocaleString('id-ID')
}

function formatDateTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('id-ID')
}

function onGateChange(gateId) {
  if (unsubscribeWs) {
    unsubscribeWs()
    unsubscribeWs = null
  }

  gateStore.clearTransaction()
  barcodeInput.value = ''

  if (!gateId) return

  const gate = websiteStore.activeGateOuts.find((g) => g.id === gateId)
  if (!gate) return

  const gateCode = gate.code || `gate-out-${gateId}`

  unsubscribeWs = $ws.on(gateCode, (event) => {
    gateStore.handleWsEvent(event)
  })

  gateStore.setWsConnected($ws.isConnected(gateCode))
}

async function onBarcodeLookup() {
  if (!barcodeInput.value.trim()) return
  const found = await gateStore.lookupTransaction({
    barcode: barcodeInput.value.trim(),
    plateNumber: barcodeInput.value.trim(),
  })
  if (!found) {
    ElMessage.warning('Transaksi tidak ditemukan')
  }
}

function openCashModal() {
  cashReceived.value = gateStore.currentTransaction?.tariff || 0
  activeMethod.value = 'cash'
  cashModalVisible.value = true
}

async function confirmCashPayment() {
  if (!selectedGate.value) return
  const gateCode = selectedGate.value.code || `gate-out-${selectedGate.value.id}`
  const success = await gateStore.confirmCashPayment({
    gateId: gateCode,
    gateOutId: selectedGate.value.id,
    paidAmount: cashReceived.value,
  })
  if (success) {
    cashModalVisible.value = false
    barcodeInput.value = ''
  }
  activeMethod.value = null
}

function startRfidPayment() {
  activeMethod.value = 'rfid'
  rfidCardNumber.value = ''
  rfidModalVisible.value = true
}

async function confirmRfidPayment() {
  if (!rfidCardNumber.value.trim() || !selectedGate.value) {
    ElMessage.warning('Masukkan nomor kartu RFID')
    return
  }
  const gateCode = selectedGate.value.code || `gate-out-${selectedGate.value.id}`
  const success = await gateStore.processRfidPayment({
    gateId: gateCode,
    gateOutId: selectedGate.value.id,
    cardNumber: rfidCardNumber.value.trim(),
  })
  if (success) {
    rfidModalVisible.value = false
    rfidCardNumber.value = ''
    barcodeInput.value = ''
  }
  activeMethod.value = null
}

function connectBooth() {
  if (boothWs) {
    try { boothWs.close() } catch (e) { /* ignore */ }
  }
  boothWs = new WebSocket('ws://localhost:5678/')
  boothWs.onopen = () => {
    console.log('Booth bridge connected')
    gateStore.setBoothConnected(true)
    if (boothWsReconnectTimer) {
      clearTimeout(boothWsReconnectTimer)
      boothWsReconnectTimer = null
    }
  }
  boothWs.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      handleBoothMessage(data)
    } catch (e) {
      console.error('Booth message parse error:', e)
    }
  }
  boothWs.onerror = () => {
    gateStore.setBoothConnected(false)
  }
  boothWs.onclose = () => {
    gateStore.setBoothConnected(false)
    // Auto-reconnect after 3s
    if (!boothWsReconnectTimer) {
      boothWsReconnectTimer = setTimeout(() => {
        boothWsReconnectTimer = null
        connectBooth()
      }, 3000)
    }
  }
}

function disconnectBooth() {
  if (boothWsReconnectTimer) {
    clearTimeout(boothWsReconnectTimer)
    boothWsReconnectTimer = null
  }
  if (boothWs) {
    try { boothWs.close() } catch (e) { /* ignore */ }
    boothWs = null
  }
  gateStore.setBoothConnected(false)
}

function handleBoothMessage(data) {
  if (data.action === 'emoney_deduct_result') {
    if (data.status === 'SUCCESS') {
      gateStore.setEmoneyState('SUCCESS')
      if (selectedGate.value) {
        const gateCode = selectedGate.value.code || `gate-out-${selectedGate.value.id}`
        gateStore.confirmEmoneyPayment({
          gateId: gateCode,
          gateOutId: selectedGate.value.id,
          deductAmount: data.deduct_amount,
          balanceAfter: data.balance_after,
          transactionCounter: data.transaction_counter,
          rawResponseHex: data.raw_response_hex,
        })
      }
    } else if (data.status === 'LOST_CONTACT') {
      gateStore.setEmoneyState('LOST_CONTACT')
      ElMessage.warning('Tap kartu lagi untuk koreksi')
    } else if (data.status === 'INSUFFICIENT_BALANCE') {
      gateStore.setEmoneyState('INSUFFICIENT')
      ElMessage.warning('Saldo tidak cukup')
    } else if (data.status === 'WRONG_CARD') {
      gateStore.setEmoneyState('WRONG_CARD')
      ElMessage.error('Kartu tidak sesuai')
    } else {
      gateStore.setEmoneyState('FAILED')
      ElMessage.error(data.error || 'E-Money gagal')
    }
    activeMethod.value = null
  }
}

function startEmoneyPayment() {
  activeMethod.value = 'emoney'
  const tx = gateStore.currentTransaction
  if (!tx?.card_number) {
    ElMessage.warning('Transaksi tidak memiliki nomor kartu e-money')
    activeMethod.value = null
    return
  }
  if (!selectedGate.value) return

  // If booth bridge is connected, use it directly
  if (gateStore.boothConnected && boothWs) {
    boothWs.send(JSON.stringify({
      action: 'emoney_deduct',
      peripheral: 'emoney_reader',
      amount: tx.tariff,
      expected_card_number: tx.card_number,
    }))
    gateStore.setEmoneyState('PROCESSING')
    return
  }

  // Fallback to API-based deduct (for manless gates or legacy mode)
  const gateCode = selectedGate.value.code || `gate-out-${selectedGate.value.id}`
  gateStore.startEmoneyDeduct({
    gateId: gateCode,
    gateOutId: selectedGate.value.id,
    cardNumber: tx.card_number,
  })
}

  async function openGateAction() {
    if (!selectedGate.value) return
    const success = await gateStore.openGate({
      gateId: selectedGate.value.id,
    })
    if (success) {
      barcodeInput.value = ''
    }
  }

  // Keyboard shortcuts
  function onKeydown(e) {
    // Space = Open Gate (when awaiting gate open)
    if (e.key === ' ') {
      e.preventDefault()
      if (gateStore.awaitingGateOpen && !gateStore.isLoading) {
        openGateAction()
        return
      }
    }
    // F1 = Cash
    if (e.key === 'F1') {
      e.preventDefault()
      if (gateStore.canPayCash && !gateStore.isLoading) {
        openCashModal()
      }
    }
    // F2 = RFID
    if (e.key === 'F2') {
      e.preventDefault()
      if (gateStore.canPayRfid && !gateStore.isLoading) {
        startRfidPayment()
      }
    }
    // F3 = E-Money
    if (e.key === 'F3') {
      e.preventDefault()
      if (gateStore.canPayEmoney && !gateStore.isLoading) {
        startEmoneyPayment()
      }
    }
    // Escape = cancel modals
    if (e.key === 'Escape') {
      cashModalVisible.value = false
      rfidModalVisible.value = false
    }
  }

// Lifecycle
onMounted(async () => {
  await websiteStore.loadAll()

  // Auto-detect booth by IP and assign default gate
  try {
    const pos = await fetchApi('/api/pos/by-ip')
    currentPos.value = pos
    if (pos.default_gate_id) {
      const gate = websiteStore.activeGateOuts.find((g) => g.id === pos.default_gate_id)
      if (gate) {
        gateStore.setSelectedGateOutId(gate.id)
        onGateChange(gate.id)
        console.log(`Auto-assigned to booth ${pos.code}, gate ${gate.name}`)
      }
    }
  } catch (err) {
    console.warn('Booth auto-detection failed:', err.message)
    // Fallback: let operator pick manually
  }

  // If no auto-assignment, pick first available
  if (!gateStore.selectedGateOutId && websiteStore.activeGateOuts.length > 0) {
    gateStore.setSelectedGateOutId(websiteStore.activeGateOuts[0].id)
    onGateChange(websiteStore.activeGateOuts[0].id)
  }

  connectBooth()
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  if (unsubscribeWs) {
    unsubscribeWs()
  }
  disconnectBooth()
  window.removeEventListener('keydown', onKeydown)
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

.ep-red {
  color: #f56c6c;
}

.open-gate-card {
  background: #f0f9eb;
  border: 1px solid #c2e7b0;
  border-radius: 8px;
}

.open-gate-btn {
  height: 56px;
  font-size: 18px;
  font-weight: 600;
  width: 100%;
}

kbd {
  background-color: #f5f5f5;
  border: 1px solid #d9d9d9;
  border-radius: 3px;
  box-shadow: 0 1px 0 rgba(0, 0, 0, 0.2);
  color: #333;
  display: inline-block;
  font-size: 13px;
  line-height: 1.4;
  padding: 1px 6px;
  white-space: nowrap;
}
</style>
