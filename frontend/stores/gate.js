/**
 * Gate Store (Pinia)
 *
 * Real-time gate-out state for the POS operator.
 * Tracks: current transaction, payment state, e-money payment state,
 * WebSocket connection status, camera snapshot, waiting seconds.
 */

import { defineStore } from 'pinia'

export const useGateStore = defineStore('gate', () => {
  // State
  const currentTransaction = ref(null)
  const paymentState = ref('IDLE') // IDLE, VEHICLE_PRESENT, WAITING_PAYMENT, TIMEOUT_ALERT
  const emoneyPaymentState = ref('IDLE') // IDLE, WAITING_CARD, PROCESSING, LOST_CONTACT, WRONG_CARD, INSUFFICIENT, SUCCESS, FAILED
  const wsConnected = ref(false)
  const boothConnected = ref(false)
  const cameraSnapshot = ref(null)
  const waitingSeconds = ref(0)
  const selectedGateOutId = ref(null)
  const alertMessage = ref(null)
  const isLoading = ref(false)

  // Getters
  const isWaitingPayment = computed(() => paymentState.value === 'WAITING_PAYMENT')
  const isTimeout = computed(() => paymentState.value === 'TIMEOUT_ALERT')
  const canPayCash = computed(() => isWaitingPayment.value || isTimeout.value)
  const canPayEmoney = computed(() => isWaitingPayment.value || isTimeout.value)
  const canPayRfid = computed(() => isWaitingPayment.value || isTimeout.value)

  // Actions

  function setTransaction(tx) {
    currentTransaction.value = tx
  }

  function clearTransaction() {
    currentTransaction.value = null
    paymentState.value = 'IDLE'
    emoneyPaymentState.value = 'IDLE'
    cameraSnapshot.value = null
    waitingSeconds.value = 0
    alertMessage.value = null
  }

  function setPaymentState(state) {
    paymentState.value = state
  }

  function setEmoneyState(state) {
    emoneyPaymentState.value = state
  }

  function setWsConnected(connected) {
    wsConnected.value = connected
  }

  function setBoothConnected(connected) {
    boothConnected.value = connected
  }

  function setCameraSnapshot(url) {
    cameraSnapshot.value = url
  }

  function setWaitingSeconds(seconds) {
    waitingSeconds.value = seconds
  }

  function setSelectedGateOutId(id) {
    selectedGateOutId.value = id
  }

  function setAlertMessage(message) {
    alertMessage.value = message
  }

  /**
   * Look up an active transaction by barcode, card, or plate.
   */
  async function lookupTransaction({ barcode, cardNumber, plateNumber }) {
    isLoading.value = true
    try {
      const { fetchApi } = useApi()
      const res = await fetchApi('/api/payments/lookup', {
        method: 'POST',
        body: JSON.stringify({
          barcode,
          card_number: cardNumber,
          plate_number: plateNumber,
        }),
      })
      if (res.found && res.transaction) {
        currentTransaction.value = {
          ...res.transaction,
          tariff: res.fee,
        }
        return true
      }
      return false
    } catch (err) {
      console.error('lookupTransaction error:', err)
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Confirm cash payment.
   */
  async function confirmCashPayment({ gateId, gateOutId, paidAmount }) {
    isLoading.value = true
    try {
      const { fetchApi } = useApi()
      const res = await fetchApi('/api/payments/cash', {
        method: 'POST',
        body: JSON.stringify({
          gate_id: gateId,
          gate_out_id: gateOutId,
          barcode: currentTransaction.value?.barcode,
          plate_number: currentTransaction.value?.plate_number,
          paid_amount: paidAmount,
        }),
      })
      if (res.success) {
        ElMessage.success(res.message)
        clearTransaction()
        return true
      } else {
        ElMessage.error(res.message)
        return false
      }
    } catch (err) {
      ElMessage.error(err.message || 'Pembayaran tunai gagal')
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Process RFID payment.
   */
  async function processRfidPayment({ gateId, gateOutId, cardNumber }) {
    isLoading.value = true
    try {
      const { fetchApi } = useApi()
      const res = await fetchApi('/api/payments/rfid', {
        method: 'POST',
        body: JSON.stringify({
          gate_id: gateId,
          gate_out_id: gateOutId,
          card_number: cardNumber,
        }),
      })
      if (res.success) {
        ElMessage.success(res.message)
        clearTransaction()
        return true
      } else {
        ElMessage.error(res.message)
        return false
      }
    } catch (err) {
      ElMessage.error(err.message || 'Pembayaran RFID gagal')
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Initiate e-money deduct.
   */
  async function startEmoneyDeduct({ gateId, gateOutId, cardNumber }) {
    isLoading.value = true
    try {
      const { fetchApi } = useApi()
      const res = await fetchApi('/api/payments/emoney/deduct', {
        method: 'POST',
        body: JSON.stringify({
          gate_id: gateId,
          gate_out_id: gateOutId,
          card_number: cardNumber,
        }),
      })
      if (res.success) {
        emoneyPaymentState.value = 'PROCESSING'
        return true
      } else {
        emoneyPaymentState.value = 'FAILED'
        ElMessage.error(res.message)
        return false
      }
    } catch (err) {
      ElMessage.error(err.message || 'E-money deduct gagal')
      emoneyPaymentState.value = 'FAILED'
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Confirm e-money payment (called after booth bridge deduct success).
   */
  async function confirmEmoneyPayment({ gateId, gateOutId, deductAmount, balanceAfter, transactionCounter, rawResponseHex }) {
    isLoading.value = true
    try {
      const { fetchApi } = useApi()
      const res = await fetchApi('/api/payments/emoney/result', {
        method: 'POST',
        body: JSON.stringify({
          gate_id: gateId,
          gate_out_id: gateOutId,
          card_number: currentTransaction.value?.card_number,
          status: 'SUCCESS',
          deduct_amount: deductAmount,
          balance_before: (currentTransaction.value?.tariff || 0) + balanceAfter,
          balance_after: balanceAfter,
          transaction_counter: transactionCounter,
          raw_response_hex: rawResponseHex,
        }),
      })
      if (res.success) {
        ElMessage.success(res.message)
        clearTransaction()
        return true
      } else {
        ElMessage.error(res.message)
        return false
      }
    } catch (err) {
      ElMessage.error(err.message || 'E-money payment failed')
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Handle incoming WebSocket event.
   */
  function handleWsEvent(event) {
    switch (event.type) {
      case 'vehicle_detected':
        paymentState.value = 'VEHICLE_PRESENT'
        // Try to lookup transaction if card number is available
        if (event.card_number) {
          lookupTransaction({ cardNumber: event.card_number })
        }
        break
      case 'gate_closed':
        paymentState.value = 'WAITING_PAYMENT'
        waitingSeconds.value = 0
        break
      case 'timeout_alert':
        paymentState.value = 'TIMEOUT_ALERT'
        alertMessage.value = `Kendaraan menunggu selama ${event.waiting_seconds || 0} detik`
        break
      case 'vehicle_passed':
      case 'vehicle_left':
        clearTransaction()
        break
      case 'deduct_result':
        if (event.status === 'SUCCESS') {
          emoneyPaymentState.value = 'SUCCESS'
          // Auto-clear after 3 seconds
          setTimeout(() => clearTransaction(), 3000)
        } else if (event.status === 'LOST_CONTACT') {
          emoneyPaymentState.value = 'LOST_CONTACT'
        } else if (event.status === 'WRONG_CARD') {
          emoneyPaymentState.value = 'WRONG_CARD'
        } else if (event.status === 'INSUFFICIENT_BALANCE') {
          emoneyPaymentState.value = 'INSUFFICIENT'
        } else {
          emoneyPaymentState.value = 'FAILED'
        }
        break
      case 'rfid_card_read':
        // Auto-process RFID if transaction exists
        if (event.card_number && currentTransaction.value) {
          // RFID handled server-side; POS gets notified
        }
        break
      default:
        break
    }
  }

  return {
    currentTransaction,
    paymentState,
    emoneyPaymentState,
    wsConnected,
    boothConnected,
    cameraSnapshot,
    waitingSeconds,
    selectedGateOutId,
    alertMessage,
    isLoading,
    isWaitingPayment,
    isTimeout,
    canPayCash,
    canPayEmoney,
    canPayRfid,
    setTransaction,
    clearTransaction,
    setPaymentState,
    setEmoneyState,
    setWsConnected,
    setBoothConnected,
    setCameraSnapshot,
    setWaitingSeconds,
    setSelectedGateOutId,
    setAlertMessage,
    lookupTransaction,
    confirmCashPayment,
    processRfidPayment,
    startEmoneyDeduct,
    confirmEmoneyPayment,
    handleWsEvent,
  }
})
