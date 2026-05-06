<template>
  <div v-if="visible" class="quick-actions">
    <div class="actions-header">
      <el-icon class="warning-icon"><WarningFilled /></el-icon>
      <span class="actions-title">{{ title }}</span>
    </div>
    <div class="actions-buttons">
      <el-button
        v-for="action in actions"
        :key="action.key"
        :type="action.type"
        :size="action.size || 'default'"
        @click="action.handler"
      >
        {{ action.label }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  paymentState: { type: String, default: 'IDLE' },
  emoneyState: { type: String, default: 'IDLE' },
})

const emit = defineEmits(['manual-open', 'reset-gate', 'vehicle-left', 'pay-cash', 'pay-rfid', 'retry-emoney', 'cancel-correction', 'override'])

const visible = computed(() => {
  return (
    props.paymentState === 'TIMEOUT_ALERT' ||
    ['INSUFFICIENT', 'WRONG_CARD', 'LOST_CONTACT', 'FAILED'].includes(props.emoneyState)
  )
})

const title = computed(() => {
  if (props.paymentState === 'TIMEOUT_ALERT') return 'Kendala: Timeout Pembayaran'
  if (props.emoneyState === 'INSUFFICIENT') return 'Kendala: Saldo Tidak Cukup'
  if (props.emoneyState === 'WRONG_CARD') return 'Kendala: Kartu Salah'
  if (props.emoneyState === 'LOST_CONTACT') return 'Kendala: Kartu Hilang Kontak'
  if (props.emoneyState === 'FAILED') return 'Kendala: Transaksi Gagal'
  return 'Kendala'
})

const actions = computed(() => {
  if (props.paymentState === 'TIMEOUT_ALERT') {
    return [
      { key: 'open', label: 'Buka Palang', type: 'warning', handler: () => emit('manual-open') },
      { key: 'reset', label: 'Reset Palang', type: 'info', handler: () => emit('reset-gate') },
      { key: 'left', label: 'Kendaraan Pergi', type: 'danger', handler: () => emit('vehicle-left') },
    ]
  }
  if (props.emoneyState === 'INSUFFICIENT') {
    return [
      { key: 'cash', label: 'Bayar Cash', type: 'success', handler: () => emit('pay-cash') },
      { key: 'rfid', label: 'Bayar RFID', type: 'primary', handler: () => emit('pay-rfid') },
      { key: 'retry', label: 'Coba Lagi', type: 'info', handler: () => emit('retry-emoney') },
    ]
  }
  if (props.emoneyState === 'WRONG_CARD') {
    return [
      { key: 'retry', label: 'Coba Lagi', type: 'info', handler: () => emit('retry-emoney') },
      { key: 'cash', label: 'Bayar Cash', type: 'success', handler: () => emit('pay-cash') },
      { key: 'rfid', label: 'Bayar RFID', type: 'primary', handler: () => emit('pay-rfid') },
    ]
  }
  if (props.emoneyState === 'LOST_CONTACT') {
    return [
      { key: 'retry', label: 'Coba Lagi', type: 'info', handler: () => emit('retry-emoney') },
      { key: 'cancel', label: 'Batalkan Koreksi', type: 'danger', handler: () => emit('cancel-correction') },
    ]
  }
  if (props.emoneyState === 'FAILED') {
    return [
      { key: 'retry', label: 'Coba Lagi', type: 'info', handler: () => emit('retry-emoney') },
      { key: 'cash', label: 'Bayar Cash', type: 'success', handler: () => emit('pay-cash') },
      { key: 'override', label: 'Override', type: 'warning', handler: () => emit('override') },
    ]
  }
  return []
})
</script>

<style scoped>
.quick-actions {
  background: var(--bg-tertiary);
  border: 1px solid var(--accent-orange);
  border-radius: 8px;
  padding: 12px;
  margin-top: 12px;
}

.actions-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.warning-icon {
  color: var(--accent-orange);
  font-size: 18px;
}

.actions-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--accent-orange);
}

.actions-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.actions-buttons .el-button {
  flex: 1;
  min-width: 120px;
}
</style>
