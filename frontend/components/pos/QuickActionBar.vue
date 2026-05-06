<template>
  <div class="quick-action-bar">
    <!-- Left: Keyboard Shortcuts -->
    <div class="shortcuts">
      <div class="shortcut" :class="{ active: canPayCash, disabled: !canPayCash }">
        <kbd>F1</kbd>
        <span>💵 Cash</span>
      </div>
      <div class="shortcut" :class="{ active: canPayRfid, disabled: !canPayRfid }">
        <kbd>F2</kbd>
        <span>🪪 RFID</span>
      </div>
      <div class="shortcut" :class="{ active: canPayEmoney, disabled: !canPayEmoney }">
        <kbd>F3</kbd>
        <span>💳 E-Money</span>
      </div>
      <div class="shortcut" :class="{ active: awaitingGateOpen, disabled: !awaitingGateOpen }">
        <kbd>Space</kbd>
        <span>🔓 Buka</span>
      </div>
      <div class="shortcut" :class="{ active: true }">
        <kbd>Esc</kbd>
        <span>✖ Batal</span>
      </div>
    </div>

    <!-- Center: State Text -->
    <div class="state-text">
      <span :class="stateTextClass">{{ stateText }}</span>
    </div>

    <!-- Right: Live Clock -->
    <div class="clock">
      {{ currentTime }}
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  paymentState: { type: String, default: 'IDLE' },
  emoneyState: { type: String, default: 'IDLE' },
  awaitingGateOpen: { type: Boolean, default: false },
  canPayCash: { type: Boolean, default: false },
  canPayRfid: { type: Boolean, default: false },
  canPayEmoney: { type: Boolean, default: false },
})

const currentTime = ref('')
let clockInterval = null

onMounted(() => {
  updateClock()
  clockInterval = setInterval(updateClock, 1000)
})

onUnmounted(() => {
  if (clockInterval) clearInterval(clockInterval)
})

function updateClock() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('id-ID', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

const stateText = computed(() => {
  if (props.awaitingGateOpen) return 'Membuka palang...'
  if (props.emoneyState !== 'IDLE') {
    switch (props.emoneyState) {
      case 'WAITING_CARD': return 'Memproses e-money...'
      case 'PROCESSING': return 'Memproses e-money...'
      case 'SUCCESS': return 'E-Money berhasil'
      case 'FAILED': return 'E-Money gagal'
      case 'INSUFFICIENT': return 'Saldo tidak cukup'
      case 'WRONG_CARD': return 'Kartu salah'
      case 'LOST_CONTACT': return 'Proses koreksi...'
      default: return ''
    }
  }
  switch (props.paymentState) {
    case 'IDLE': return 'Siap'
    case 'VEHICLE_PRESENT': return 'Kendaraan terdeteksi'
    case 'WAITING_PAYMENT': return 'Menunggu pembayaran'
    case 'TIMEOUT_ALERT': return '⚠️ Timeout — butuh intervensi'
    default: return ''
  }
})

const stateTextClass = computed(() => {
  if (props.paymentState === 'TIMEOUT_ALERT') return 'state-timeout'
  if (props.emoneyState === 'SUCCESS' || props.paymentState === 'WAITING_PAYMENT') return 'state-ok'
  if (['FAILED', 'INSUFFICIENT', 'WRONG_CARD'].includes(props.emoneyState)) return 'state-error'
  return ''
})
</script>

<style scoped>
.quick-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 50px;
  padding: 0 16px;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
}

.shortcuts {
  display: flex;
  gap: 8px;
}

.shortcut {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 4px;
  background: var(--bg-tertiary);
  transition: all 0.15s ease;
}

.shortcut.active {
  background: var(--bg-hover);
  border: 1px solid var(--border-active);
}

.shortcut.disabled {
  opacity: 0.4;
}

.shortcut kbd {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-primary);
  background: var(--bg-hover);
  padding: 2px 6px;
  border-radius: 3px;
  border: 1px solid var(--border-color);
  font-family: monospace;
}

.shortcut span {
  font-size: 12px;
  color: var(--text-secondary);
}

.state-text {
  flex: 1;
  text-align: center;
}

.state-text span {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

.state-ok span {
  color: var(--accent-green) !important;
}

.state-error span {
  color: var(--accent-red) !important;
}

.state-timeout span {
  color: var(--accent-orange) !important;
  animation: flash 1s ease-in-out infinite;
}

@keyframes flash {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.clock {
  font-size: 16px;
  font-weight: 700;
  font-family: 'Courier New', monospace;
  color: var(--text-primary);
  min-width: 80px;
  text-align: right;
}
</style>
