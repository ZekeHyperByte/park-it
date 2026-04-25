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
  const cameraSnapshot = ref(null)
  const waitingSeconds = ref(0)
  const selectedGateOutId = ref(null)
  const alertMessage = ref(null)

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
   * Handle incoming WebSocket event.
   */
  function handleWsEvent(event) {
    switch (event.type) {
      case 'vehicle_detected':
        paymentState.value = 'VEHICLE_PRESENT'
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
        // RFID exit handled server-side; POS gets notified via transaction update
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
    cameraSnapshot,
    waitingSeconds,
    selectedGateOutId,
    alertMessage,
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
    setCameraSnapshot,
    setWaitingSeconds,
    setSelectedGateOutId,
    setAlertMessage,
    handleWsEvent,
  }
})
