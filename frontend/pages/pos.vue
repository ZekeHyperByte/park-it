<template>
  <NuxtLayout name="kiosk">
    <template #status-bar>
      <PosStatusBar
        :gate-name="selectedGate?.name || '--'"
        :ws-connected="gateStore.wsConnected"
        :hardware-status="hardwareStatus"
        :transaction-count="posSession.transactionCount"
        :cash-collected="posSession.cashCollected"
      />
    </template>

    <!-- Main: State-driven single-column layout -->
    <div :class="['h-full overflow-hidden', timeoutBorderClass]">
      <!-- GATE_OPEN: awaiting gate open after payment -->
      <PosGateOpenView
        v-if="viewState === 'GATE_OPEN'"
        :change-amount="gateStore.changeAmount"
        :plate-number="gateStore.currentTransaction?.plate_number || ''"
        @open-gate="openGateAction"
      />

      <!-- ERROR: timeout or e-money errors -->
      <PosErrorView
        v-else-if="viewState === 'ERROR'"
        :payment-state="gateStore.paymentState"
        :emoney-state="gateStore.emoneyPaymentState"
        :waiting-seconds="gateStore.waitingSeconds"
        :plate-number="gateStore.currentTransaction?.plate_number || ''"
        @manual-open="openGateAction"
        @vehicle-left="vehicleLeftAction"
        @pay-cash="showCashDialog = true"
        @pay-rfid="showRfidDialog = true"
        @retry-emoney="retryEmoney"
        @cancel-correction="cancelCorrection"
      />

      <!-- UNIFIED: consistent layout for both IDLE and ACTIVE states -->
      <PosUnifiedView
        v-else
        ref="unifiedViewRef"
        :transaction="gateStore.currentTransaction"
        :duration-seconds="gateStore.durationSeconds"
        :waiting-seconds="gateStore.waitingSeconds"
        :payment-state="gateStore.paymentState"
        :emoney-state="gateStore.emoneyPaymentState"
        :vehicle-types="websiteStore.vehicleTypes"
        :entry-photo-url="entryPhotoUrl"
        :exit-photo-url="exitPhotoUrl"
        :timeout-seconds="timeoutSeconds"
        :can-pay-cash="gateStore.canPayCash"
        :can-pay-rfid="gateStore.canPayRfid"
        :can-pay-emoney="gateStore.canPayEmoney"
        :card-info="emoneyCardInfo"
        :balance="emoneyBalance"
        :awaiting-gate-open="gateStore.awaitingGateOpen"
        :is-processing="isPaymentProcessing"
        @barcode-lookup="onBarcodeLookup"
        @pay-cash="showCashDialog = true"
        @pay-rfid="showRfidDialog = true"
        @pay-emoney="startEmoneyPayment"
        @retry-emoney="retryEmoney"
        @cancel-emoney="cancelEmoney"
      />
    </div>

    <template #action-bar>
      <QuickActionBar
        :payment-state="gateStore.paymentState"
        :emoney-state="gateStore.emoneyPaymentState"
        :awaiting-gate-open="gateStore.awaitingGateOpen"
        :can-pay-cash="gateStore.canPayCash"
        :can-pay-rfid="gateStore.canPayRfid"
        :can-pay-emoney="gateStore.canPayEmoney"
        :gate-name="selectedGate?.name || ''"
        :shift-name="posSession.shiftName"
      />
    </template>

    <!-- Cash Dialog -->
    <CashDialog
      v-model:open="showCashDialog"
      :tariff="currentTariff"
      @confirm="confirmCashPayment"
    />

    <!-- RFID Dialog -->
    <RfidDialog
      v-model:open="showRfidDialog"
      @confirm="confirmRfidPayment"
    />
  </NuxtLayout>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useKeyboard } from '~/composables/useKeyboard'
import { useFormatters } from '~/composables/useFormatters'

definePageMeta({
  middleware: 'auth',
  layout: false,
})

const authStore = useAuthStore()
const websiteStore = useWebsiteStore()
const gateStore = useGateStore()
const posSession = usePosSessionStore()
const { $ws } = useNuxtApp()
const config = useRuntimeConfig()
const { fetchApi } = useApi()
const sound = useSound()
const { hardwareStatus, updateFromGate, updateWebSocketStatus, startPolling, stopPolling } = useHardwareStatus()
const { detectCardType, maskCardNumber } = useFormatters()

// Refs
let unsubscribeWs = null
let boothWs = null
let boothWsReconnectTimer = null
let boothWsReconnectAttempts = 0
const BOOTH_MAX_RECONNECT_ATTEMPTS = 10
const showCashDialog = ref(false)
const showRfidDialog = ref(false)
const emoneyBalance = ref(null)
const isPaymentProcessing = ref(false)
const recentTransactions = ref([])
const unifiedViewRef = ref(null)

// View state (priority: GATE_OPEN > ERROR > UNIFIED)
// UNIFIED view is always shown unless we're in a special state
const viewState = computed(() => {
  if (gateStore.awaitingGateOpen) return 'GATE_OPEN'
  if (
    gateStore.paymentState === 'TIMEOUT_ALERT' ||
    ['LOST_CONTACT', 'WRONG_CARD', 'INSUFFICIENT', 'FAILED'].includes(gateStore.emoneyPaymentState)
  ) {
    return 'ERROR'
  }
  return 'UNIFIED' // Always show unified view (handles both IDLE and ACTIVE)
})

// Timeout border class — ring overlay at 70%/90% thresholds
const timeoutBorderClass = computed(() => {
  if (!gateStore.currentTransaction || viewState.value !== 'UNIFIED') return ''
  const percent = timeoutSeconds.value > 0
    ? (gateStore.waitingSeconds / timeoutSeconds.value) * 100
    : 0
  if (percent >= 90) return 'ring-2 ring-inset ring-destructive/60'
  if (percent >= 70) return 'ring-2 ring-inset ring-warning/40'
  return ''
})

// Computed
const selectedGate = computed(() =>
  websiteStore.activeGateOuts.find((g) => g.id === gateStore.selectedGateOutId)
)

const currentTariff = computed(() =>
  gateStore.currentTransaction?.tariff || gateStore.currentTransaction?.fee || 0
)

const timeoutSeconds = computed(() =>
  parseInt(websiteStore.getSetting('payment_timeout_seconds', '120'))
)

const entryPhotoUrl = computed(() => {
  const tx = gateStore.currentTransaction
  if (!tx?.entry_snapshot_id) return null
  return `/api/snapshots/${tx.entry_snapshot_id}/image`
})

const exitPhotoUrl = computed(() => gateStore.cameraSnapshot)

const emoneyCardInfo = computed(() => {
  const tx = gateStore.currentTransaction
  if (!tx?.card_number) return null
  return {
    cardType: detectCardType(tx.card_number),
    cardNumber: maskCardNumber(tx.card_number),
  }
})

// Focus management on view transitions
watch(viewState, (newState) => {
  nextTick(() => {
    if (newState === 'UNIFIED') {
      unifiedViewRef.value?.focusBarcode?.()
    }
  })
})

// Keyboard shortcuts
useKeyboard([
  { keys: ['F1'], action: () => gateStore.canPayCash && (showCashDialog.value = true) },
  { keys: ['F2'], action: () => gateStore.canPayRfid && (showRfidDialog.value = true) },
  { keys: ['F3'], action: () => gateStore.canPayEmoney && startEmoneyPayment() },
  { keys: [' '], action: () => gateStore.awaitingGateOpen && openGateAction() },
  { keys: ['Escape'], action: () => { showCashDialog.value = false; showRfidDialog.value = false } },
])

// Actions
async function onBarcodeLookup(input) {
  if (!input.trim()) return
  const found = await gateStore.lookupTransaction({
    barcode: input.trim(),
    plateNumber: input.trim(),
  })
  if (!found) {
    toast.warning('Transaksi tidak ditemukan')
  }
}

async function confirmCashPayment(amount) {
  if (!selectedGate.value || isPaymentProcessing.value) return
  isPaymentProcessing.value = true
  try {
    const gateCode = selectedGate.value.code || `gate-out-${selectedGate.value.id}`
    const result = await gateStore.confirmCashPayment({
      gateId: gateCode,
      gateOutId: selectedGate.value.id,
      paidAmount: amount,
    })
    if (result?.success) {
      sound.paymentSuccess()
      posSession.addCashPayment(amount - (result.change_amount || 0))
      toast.success('Pembayaran berhasil. Tekan Space untuk buka palang.')
    } else {
      toast.error(result?.message || 'Pembayaran tunai gagal')
    }
  } finally {
    isPaymentProcessing.value = false
  }
}

async function confirmRfidPayment(cardNumber) {
  if (!cardNumber.trim() || !selectedGate.value || isPaymentProcessing.value) {
    if (!cardNumber.trim()) toast.warning('Masukkan nomor kartu RFID')
    return
  }
  isPaymentProcessing.value = true
  try {
    const gateCode = selectedGate.value.code || `gate-out-${selectedGate.value.id}`
    const result = await gateStore.processRfidPayment({
      gateId: gateCode,
      gateOutId: selectedGate.value.id,
      cardNumber: cardNumber.trim(),
    })
    if (result?.success) {
      sound.paymentSuccess()
      posSession.addTransaction()
      toast.success(result.message || 'Pembayaran RFID berhasil')
    } else {
      toast.error(result?.message || 'Pembayaran RFID gagal')
    }
  } finally {
    isPaymentProcessing.value = false
  }
}

function startEmoneyPayment() {
  const tx = gateStore.currentTransaction
  if (!tx?.card_number) {
    toast.warning('Transaksi tidak memiliki nomor kartu e-money')
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
  toast.info('Koreksi dibatalkan')
}

async function openGateAction() {
  if (!selectedGate.value) return
  const result = await gateStore.openGate({ gateId: selectedGate.value.id })
  if (result?.success) {
    sound.gateOpen()
    toast.success('Palang pintu dibuka')
  } else {
    toast.error(result?.message || 'Gagal membuka palang')
  }
}

function vehicleLeftAction() {
  gateStore.clearTransaction()
  toast.info('Kendaraan pergi — transaksi dibersihkan')
}

// Booth bridge connection
function connectBooth() {
  if (boothWs) {
    try { boothWs.close() } catch (e) { /* ignore */ }
  }

  if (boothWsReconnectAttempts >= BOOTH_MAX_RECONNECT_ATTEMPTS) {
    console.warn('Booth bridge: max reconnect attempts reached, giving up')
    gateStore.setBoothConnected(false)
    return
  }

  const boothUrl = config.public.boothBridgeUrl || 'ws://localhost:5678/'
  boothWs = new WebSocket(boothUrl)
  boothWs.onopen = () => {
    gateStore.setBoothConnected(true)
    boothWsReconnectAttempts = 0
    if (boothWsReconnectTimer) {
      clearTimeout(boothWsReconnectTimer)
      boothWsReconnectTimer = null
    }
  }
  boothWs.onmessage = (event) => {
    try {
      handleBoothMessage(JSON.parse(event.data))
    } catch (e) {
      console.error('Booth message parse error:', e)
    }
  }
  boothWs.onerror = () => gateStore.setBoothConnected(false)
  boothWs.onclose = () => {
    gateStore.setBoothConnected(false)
    if (!boothWsReconnectTimer) {
      boothWsReconnectAttempts++
      const delay = Math.min(3000 * Math.pow(2, boothWsReconnectAttempts - 1), 60000)
      boothWsReconnectTimer = setTimeout(() => {
        boothWsReconnectTimer = null
        connectBooth()
      }, delay)
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
      toast.success('Pembayaran e-money berhasil')
    } else if (data.status === 'LOST_CONTACT') {
      gateStore.setEmoneyState('LOST_CONTACT')
      sound.paymentFailed()
      toast.warning('Tap kartu lagi untuk koreksi')
    } else if (data.status === 'INSUFFICIENT_BALANCE') {
      gateStore.setEmoneyState('INSUFFICIENT')
      sound.paymentFailed()
      toast.warning('Saldo tidak cukup')
    } else if (data.status === 'WRONG_CARD') {
      gateStore.setEmoneyState('WRONG_CARD')
      sound.paymentFailed()
      toast.error('Kartu tidak sesuai')
    } else {
      gateStore.setEmoneyState('FAILED')
      sound.paymentFailed()
      toast.error(data.error || 'E-Money gagal')
    }
  }
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

  const gateCode = gate.code || `gateway-out-${gateId}`

  unsubscribeWs = $ws.on(gateCode, (event) => {
    gateStore.handleWsEvent(event)

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

// Toast helper (using vue-sonner)
const toast = {
  success: (msg) => useNuxtApp().$toast?.success?.(msg) || console.log('[success]', msg),
  error: (msg) => useNuxtApp().$toast?.error?.(msg) || console.error('[error]', msg),
  warning: (msg) => useNuxtApp().$toast?.warning?.(msg) || console.warn('[warning]', msg),
  info: (msg) => useNuxtApp().$toast?.info?.(msg) || console.log('[info]', msg),
}

// Lifecycle
onMounted(async () => {
  await websiteStore.loadAll()
  await posSession.loadShiftSummary()

  // Auto-detect booth by IP
  let gateDetected = false
  try {
    const pos = await fetchApi('/api/pos/by-ip')
    if (pos.default_gate_id) {
      const gate = websiteStore.activeGateOuts.find((g) => g.id === pos.default_gate_id)
      if (gate) {
        gateStore.setSelectedGateOutId(gate.id)
        onGateChange(gate.id)
        gateDetected = true
        toast.info(`Terhubung ke ${gate.name}`)
      }
    }
  } catch (err) {
    console.warn('Booth auto-detection failed:', err.message)
  }

  // Fallback to first available gate
  if (!gateDetected && websiteStore.activeGateOuts.length > 0) {
    const fallbackGate = websiteStore.activeGateOuts[0]
    gateStore.setSelectedGateOutId(fallbackGate.id)
    onGateChange(fallbackGate.id)
    toast.warning(`Auto-deteksi gagal, menggunakan ${fallbackGate.name}`)
  }

  connectBooth()
  startPolling(60000)
})

onBeforeUnmount(() => {
  if (unsubscribeWs) {
    unsubscribeWs()
    unsubscribeWs = null
  }
  disconnectBooth()
  stopPolling()
  gateStore.stopDurationTimer()
})
</script>
