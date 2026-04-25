import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('#app', () => ({
  useRuntimeConfig: () => ({
    public: { apiBaseUrl: 'http://localhost:8000' },
  }),
}))

vi.mock('../../composables/useApi.js', () => ({
  useApi: () => ({
    fetchApi: vi.fn(),
  }),
}))

describe('Gate Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should have initial idle state', async () => {
    const { useGateStore } = await import('../../stores/gate.js')
    const store = useGateStore()

    expect(store.paymentState).toBe('IDLE')
    expect(store.emoneyPaymentState).toBe('IDLE')
    expect(store.currentTransaction).toBeNull()
    expect(store.wsConnected).toBe(false)
  })

  it('should set transaction', async () => {
    const { useGateStore } = await import('../../stores/gate.js')
    const store = useGateStore()
    const tx = { id: 1, barcode: 'T001' }

    store.setTransaction(tx)
    expect(store.currentTransaction).toEqual(tx)
  })

  it('should clear transaction and reset states', async () => {
    const { useGateStore } = await import('../../stores/gate.js')
    const store = useGateStore()
    store.setTransaction({ id: 1 })
    store.setPaymentState('WAITING_PAYMENT')
    store.setEmoneyState('PROCESSING')

    store.clearTransaction()

    expect(store.currentTransaction).toBeNull()
    expect(store.paymentState).toBe('IDLE')
    expect(store.emoneyPaymentState).toBe('IDLE')
  })

  it('should handle vehicle_detected event', async () => {
    const { useGateStore } = await import('../../stores/gate.js')
    const store = useGateStore()

    store.handleWsEvent({ type: 'vehicle_detected' })
    expect(store.paymentState).toBe('VEHICLE_PRESENT')
  })

  it('should handle timeout_alert event', async () => {
    const { useGateStore } = await import('../../stores/gate.js')
    const store = useGateStore()

    store.handleWsEvent({ type: 'timeout_alert', waiting_seconds: 125 })
    expect(store.paymentState).toBe('TIMEOUT_ALERT')
    expect(store.alertMessage).toContain('125')
  })

  it('should handle deduct_result SUCCESS', async () => {
    const { useGateStore } = await import('../../stores/gate.js')
    const store = useGateStore()

    store.handleWsEvent({ type: 'deduct_result', status: 'SUCCESS' })
    expect(store.emoneyPaymentState).toBe('SUCCESS')
  })

  it('should handle deduct_result LOST_CONTACT', async () => {
    const { useGateStore } = await import('../../stores/gate.js')
    const store = useGateStore()

    store.handleWsEvent({ type: 'deduct_result', status: 'LOST_CONTACT' })
    expect(store.emoneyPaymentState).toBe('LOST_CONTACT')
  })

  it('should handle deduct_result INSUFFICIENT_BALANCE', async () => {
    const { useGateStore } = await import('../../stores/gate.js')
    const store = useGateStore()

    store.handleWsEvent({ type: 'deduct_result', status: 'INSUFFICIENT_BALANCE' })
    expect(store.emoneyPaymentState).toBe('INSUFFICIENT')
  })

  it('should enable pay buttons when waiting payment', async () => {
    const { useGateStore } = await import('../../stores/gate.js')
    const store = useGateStore()

    expect(store.canPayCash).toBe(false)
    store.setPaymentState('WAITING_PAYMENT')
    expect(store.canPayCash).toBe(true)
    expect(store.canPayEmoney).toBe(true)
    expect(store.canPayRfid).toBe(true)
  })
})
