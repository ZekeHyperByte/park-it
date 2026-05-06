<template>
  <div class="pos-page">
    <!-- Zone 1: Status Bar -->
    <StatusBar
      :gate="selectedGate"
      :hardware-status="hardwareStatus"
      :user="authStore.user"
      :cash-collected="cashCollected"
      :transaction-count="transactionCount"
      :shift-info="shiftInfo"
    />

    <!-- Zone 2: Main Area (60/40 split) -->
    <div class="main-area">
      <!-- Left: Vehicle Info Card -->
      <VehicleInfoCard
        :transaction="gateStore.currentTransaction"
        :duration-seconds="gateStore.durationSeconds"
        :waiting-seconds="gateStore.waitingSeconds"
        :payment-state="gateStore.paymentState"
        :emoney-state="gateStore.emoneyPaymentState"
        :vehicle-types="websiteStore.vehicleTypes"
        :entry-photo-url="entryPhotoUrl"
        :exit-photo-url="exitPhotoUrl"
        :timeout-seconds="timeoutSeconds"
        @lookup="onBarcodeLookup"
        @manual-open="openGateAction"
        @reset-gate="resetGateAction"
        @vehicle-left="vehicleLeftAction"
        @pay-cash="openCashModal"
        @pay-rfid="startRfidPayment"
        @retry-emoney="retryEmoney"
        @cancel-correction="cancelCorrection"
        @override="overrideAction"
      />

      <!-- Right: Payment Panel -->
      <PaymentPanel
        ref="paymentPanelRef"
        :payment-state="gateStore.paymentState"
        :emoney-state="gateStore.emoneyPaymentState"
        :awaiting-gate-open="gateStore.awaitingGateOpen"
        :tariff="currentTariff"
        :change-amount="gateStore.changeAmount"
        :emoney-card-info="emoneyCardInfo"
        :emoney-balance="emoneyBalance"
        @pay-cash="openCashModal"
        @pay-rfid="startRfidPayment"
        @pay-emoney="startEmoneyPayment"
        @open-gate="openGateAction"
        @cancel-emoney="cancelEmoney"
        @retry-emoney="retryEmoney"
        @barcode-lookup="onBarcodeLookupInput"
        @confirm-cash="confirmCashPayment"
        @confirm-rfid="confirmRfidPayment"
      />
    </div>

    <!-- Zone 3: Quick Action Bar -->
    <QuickActionBar
      :payment-state="gateStore.paymentState"
      :emoney-state="gateStore.emoneyPaymentState"
      :awaiting-gate-open="gateStore.awaitingGateOpen"
      :can-pay-cash="gateStore.canPayCash"
      :can-pay-rfid="gateStore.canPayRfid"
      :can-pay-emoney="gateStore.canPayEmoney"
    />
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import StatusBar from '~/components/pos/StatusBar.vue'
import VehicleInfoCard from '~/components/pos/VehicleInfoCard.vue'
import PaymentPanel from '~/components/pos/PaymentPanel.vue'
import QuickActionBar from '~/components/pos/QuickActionBar.vue'

definePageMeta({
  middleware: 'auth',
})

const authStore = useAuthStore()
const websiteStore = useWebsiteStore()
const gateStore = useGateStore()
const { $ws } = useNuxtApp()
const { fetchApi } = useApi()
const sound = useSound()
const { hardwareStatus, updateFromGate, updateWebSocketStatus, startPolling, stopPolling } = useHardwareStatus()

// Refs
const paymentPanelRef = ref(null)
let unsubscribeWs = null
let boothWs = null
let boothWsReconnectTimer = null

// Booth auto-detection
const currentPos = ref(null)
const isAdmin = computed(() => authStore.user?.role === 'admin')

// Shift counter state
const cashCollected = ref(0)
const transactionCount = ref(0)
const shiftInfo = ref(null)

// Timeout config (default 120s)
const timeoutSeconds = computed(() => {
  return parseInt(websiteStore.getSetting('payment_timeout_seconds', '120'))
})

// Computed
const selectedGate = computed(() =>
  websiteStore.activeGateOuts.find((g) => g.id === gateStore.selectedGateOutId)
)

const currentTariff = computed(() => {
  return gateStore.currentTransaction?.tariff || gateStore.currentTransaction?.fee || 0
})

const entryPhotoUrl = computed(() => {
  const tx = gateStore.currentTransaction
  if (!tx?.entry_snapshot_id) return null
  return `/api/snapshots/${tx.entry_snapshot_id}/image`
})

const exitPhotoUrl = computed(() => {
  return gateStore.cameraSnapshot
})

const emoneyCardInfo = computed(() => {
  const tx = gateStore.currentTransaction
  if (!tx?.card_number) return null
  return {
    cardType: detectCardType(tx.card_number),
    cardNumber: maskCardNumber(tx.card_number),
  }
})

const emoneyBalance = ref(null)

// Methods
function detectCardNumber(cardNumber) {
  if (!cardNumber) return 'Unknown'
  if (cardNumber.startsWith('00') || cardNumber.startsWith('01')) return 'Mandiri eMoney'
  if (cardNumber.startsWith('02')) return 'BRI Brizzi'
  if (cardNumber.startsWith('03')) return 'BNI TapCash'
  if (cardNumber.startsWith('04')) return 'BCA Flazz'
  return 'E-Money'
}

function maskCardNumber(cardNumber) {
  if (!cardNumber || cardNumber.length < 8) return '****'
  const last4 = cardNumber.slice(-4)
  return `**** **** **** ${last4}`
}

function formatCurrency(amount) {
  return `Rp ${new Intl.NumberFormat('id-ID').format(amount)}`
}

function onBarcodeLookup() {
  if (paymentPanelRef.value) {
    paymentPanelRef.value.openCashModal()
  }
}

async function onBarcodeLookupInput(input) {
  if (!input.trim()) return
  const found = await gateStore.lookupTransaction({
    barcode: input.trim(),
    plateNumber: input.trim(),
  })
  if (!found) {
    ElMessage.warning('Transaksi tidak ditemukan')
  }
}

function openCashModal() {
  if (paymentPanelRef.value) {
    paymentPanelRef.value.openCashModal()
  }
}

async function confirmCashPayment(amount) {
  if (!selectedGate.value) return
  const gateCode = selectedGate.value.code || `gate-out-${selectedGate.value.id}`
  const result = await gateStore.confirmCashPayment({
    gateId: gateCode,
    gateOutId: selectedGate.value.id,
    paidAmount: amount,
  })
  if (result) {
    sound.paymentSuccess()
    cashCollected.value += amount - (result.change_amount || 0)
    transactionCount.value++
  }
}

function startRfidPayment() {
  if (paymentPanelRef.value) {
    paymentPanelRef.value.openRfidModal()
  }
}

async function confirmRfidPayment(cardNumber) {
  if (!cardNumber.trim() || !selectedGate.value) {
    ElMessage.warning('Masukkan nomor kartu RFID')
    return
  }
  const gateCode = selectedGate.value.code || `gate-out-${selectedGate.value.id}`
  const success = await gateStore.processRfidPayment({
    gateId: gateCode,
    gateOutId: selectedGate.value.id,
    cardNumber: cardNumber.trim(),
  })
  if (success) {
    sound.paymentSuccess()
    transactionCount.value++
  }
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
      emoneyBalance.value = data.balance_after
      sound.paymentSuccess()
      if (selectedGate.value) {
        const gateCode = selectedGate.value.code || `gate-out-${selectedGate.value.id}`
        gateStore.confirmEmoneyPayment({
          gateId: gateCode,
          gateOutId: selectedGate.value.id,
          cardNumber: data.card_number,
          deductAmount: data.deduct_amount,
          balanceBefore: data.balance_before,
          balanceAfter: data.balance_after,
          transactionCounter: data.transaction_counter,
          rawResponseHex: data.raw_response_hex,
        })
      }
    } else if (data.status === 'LOST_CONTACT') {
      gateStore.setEmoneyState('LOST_CONTACT')
      sound.paymentFailed()
      ElMessage.warning('Tap kartu lagi untuk koreksi')
    } else if (data.status === 'INSUFFICIENT_BALANCE') {
      gateStore.setEmoneyState('INSUFFICIENT')
      sound.paymentFailed()
      ElMessage.warning('Saldo tidak cukup')
    } else if (data.status === 'WRONG_CARD') {
      gateStore.setEmoneyState('WRONG_CARD')
      sound.paymentFailed()
      ElMessage.error('Kartu tidak sesuai')
    } else {
      gateStore.setEmoneyState('FAILED')
      sound.paymentFailed()
      ElMessage.error(data.error || 'E-Money gagal')
    }
  }
}

function startEmoneyPayment() {
  const tx = gateStore.currentTransaction
  if (!tx?.card_number) {
    ElMessage.warning('Transaksi tidak memiliki nomor kartu e-money')
    return
  }
  if (!selectedGate.value) return

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

  const gateCode = selectedGate.value.code || `gate-out-${selectedGate.value.id}`
  gateStore.startEmoneyDeduct({
    gateId: gateCode,
    gateOutId: selectedGate.value.id,
    cardNumber: tx.card_number,
  })
}

function cancelEmoney() {
  gateStore.setEmoneyState('IDLE')
}

function retryEmoney() {
  gateStore.setEmoneyState('IDLE')
  startEmoneyPayment()
}

function cancelCorrection() {
  gateStore.setEmoneyState('IDLE')
  ElMessage.info('Koreksi dibatalkan')
}

function overrideAction() {
  ElMessage.warning('Override memerlukan hak admin')
}

async function openGateAction() {
  if (!selectedGate.value) return
  const success = await gateStore.openGate({
    gateId: selectedGate.value.id,
  })
  if (success) {
    sound.gateOpen()
  }
}

function resetGateAction() {
  ElMessage.info('Reset palang — kirim perintah ke daemon')
}

function vehicleLeftAction() {
  gateStore.clearTransaction()
  ElMessage.info('Kendaraan pergi — transaksi dibersihkan')
}

function onGateChange(gateId) {
  if (unsubscribeWs) {
    unsubscribeWs()
    unsubscribeWs = null
  }

  gateStore.clearTransaction()

  if (!gateId) return

  const gate = websiteStore.activeGateOuts.find((g) => g.id === gateId)
  if (!gate) return

  const gateCode = gate.code || `gate-out-${gateId}`

  unsubscribeWs = $ws.on(gateCode, (event) => {
    gateStore.handleWsEvent(event)

    // Sound feedback on events
    if (event.type === 'vehicle_detected') {
      sound.vehicleDetected()
    } else if (event.type === 'timeout_alert') {
      sound.timeoutAlert()
    }
  })

  gateStore.setWsConnected($ws.isConnected(gateCode))
  updateWebSocketStatus($ws.isConnected(gateCode))
  updateFromGate(gate)
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
  }

  // If no auto-assignment, pick first available
  if (!gateStore.selectedGateOutId && websiteStore.activeGateOuts.length > 0) {
    gateStore.setSelectedGateOutId(websiteStore.activeGateOuts[0].id)
    onGateChange(websiteStore.activeGateOuts[0].id)
  }

  // Load shift info
  const now = new Date()
  const shiftName = websiteStore.getSetting('current_shift_name', '')
  const shiftStart = websiteStore.getSetting('current_shift_start', '')
  const shiftEnd = websiteStore.getSetting('current_shift_end', '')
  if (shiftName) {
    shiftInfo.value = {
      name: shiftName,
      timeRange: shiftStart && shiftEnd ? `${shiftStart}-${shiftEnd}` : '',
    }
  }

  connectBooth()
  startPolling(60000)

  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  if (unsubscribeWs) {
    unsubscribeWs()
  }
  disconnectBooth()
  stopPolling()
  gateStore.stopDurationTimer()
  window.removeEventListener('keydown', onKeydown)
})

// Keyboard shortcuts
function onKeydown(e) {
  if (e.key === ' ') {
    e.preventDefault()
    if (gateStore.awaitingGateOpen && !gateStore.isLoading) {
      openGateAction()
      return
    }
  }
  if (e.key === 'F1') {
    e.preventDefault()
    if (gateStore.canPayCash && !gateStore.isLoading) {
      openCashModal()
    }
  }
  if (e.key === 'F2') {
    e.preventDefault()
    if (gateStore.canPayRfid && !gateStore.isLoading) {
      startRfidPayment()
    }
  }
  if (e.key === 'F3') {
    e.preventDefault()
    if (gateStore.canPayEmoney && !gateStore.isLoading) {
      startEmoneyPayment()
    }
  }
  if (e.key === 'Escape') {
    if (paymentPanelRef.value) {
      paymentPanelRef.value.closeModals()
    }
  }
  if (e.key === 'Enter') {
    if (paymentPanelRef.value) {
      // Enter is handled inside PaymentPanel modals
    }
  }
}
</script>

<style scoped>
.pos-page {
  display: grid;
  grid-template-rows: 60px 1fr 50px;
  height: 100vh;
  background: var(--bg-primary);
  overflow: hidden;
}

.main-area {
  display: grid;
  grid-template-columns: 3fr 2fr;
  gap: 16px;
  padding: 16px;
  overflow: hidden;
  min-height: 0;
}
</style>
