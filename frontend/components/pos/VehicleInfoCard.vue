<template>
  <div class="vehicle-info-card">
    <!-- Photo Comparison -->
    <PhotoComparison
      :entry-photo-url="entryPhotoUrl"
      :exit-photo-url="exitPhotoUrl"
      :entry-time="transaction?.entry_time"
      :exit-time="transaction?.exit_time"
      :entry-gate-name="transaction?.gate_in_name"
      :exit-gate-name="transaction?.gate_out_name"
    />

    <!-- Vehicle Details -->
    <div class="vehicle-details">
      <div class="plate-row">
        <span class="plate-icon">🚗</span>
        <span class="plate-number">{{ transaction?.plate_number || '---' }}</span>
        <el-button size="small" @click="$emit('lookup')">
          <el-icon><Search /></el-icon>
        </el-button>
      </div>

      <div class="vehicle-type">{{ vehicleTypeName }}</div>

      <div class="details-divider"></div>

      <div class="detail-row">
        <span class="detail-label">Durasi</span>
        <span class="detail-value">{{ durationText }}</span>
      </div>

      <div class="detail-row">
        <span class="detail-label">Tarif</span>
        <span class="detail-value tariff">{{ formatCurrency(tariff) }}</span>
      </div>

      <div class="detail-row">
        <span class="detail-label">Masuk</span>
        <span class="detail-value">{{ entryTimeText }}</span>
      </div>

      <div class="detail-row">
        <span class="detail-label">Status</span>
        <span class="detail-value" :class="statusClass">{{ statusText }}</span>
      </div>

      <!-- Timeout Progress Bar -->
      <div v-if="showTimeoutBar" class="timeout-section">
        <div class="timeout-label">
          <span>⏱️ {{ formatWaitingSeconds(waitingSeconds) }}</span>
          <span>{{ timeoutPercent }}%</span>
        </div>
        <div class="timeout-bar-bg">
          <div
            class="timeout-bar-fill"
            :class="timeoutBarClass"
            :style="{ width: `${Math.min(timeoutPercent, 100)}%` }"
          ></div>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <QuickActions
      :payment-state="paymentState"
      :emoney-state="emoneyState"
      @manual-open="$emit('manual-open')"
      @reset-gate="$emit('reset-gate')"
      @vehicle-left="$emit('vehicle-left')"
      @pay-cash="$emit('pay-cash')"
      @pay-rfid="$emit('pay-rfid')"
      @retry-emoney="$emit('retry-emoney')"
      @cancel-correction="$emit('cancel-correction')"
      @override="$emit('override')"
    />
  </div>
</template>

<script setup>
const props = defineProps({
  transaction: { type: Object, default: null },
  durationSeconds: { type: Number, default: 0 },
  waitingSeconds: { type: Number, default: 0 },
  paymentState: { type: String, default: 'IDLE' },
  emoneyState: { type: String, default: 'IDLE' },
  vehicleTypes: { type: Array, default: () => [] },
  entryPhotoUrl: { type: String, default: null },
  exitPhotoUrl: { type: String, default: null },
  timeoutSeconds: { type: Number, default: 120 },
})

const emit = defineEmits(['lookup', 'manual-open', 'reset-gate', 'vehicle-left', 'pay-cash', 'pay-rfid', 'retry-emoney', 'cancel-correction', 'override'])

const tariff = computed(() => props.transaction?.tariff || props.transaction?.fee || 0)

const vehicleTypeName = computed(() => {
  const vtId = props.transaction?.vehicle_type_id
  if (!vtId) return '--'
  const vt = props.vehicleTypes.find(v => v.id === vtId)
  return vt ? `${vt.name}` : '--'
})

const durationText = computed(() => {
  if (!props.durationSeconds) return '0j 0m'
  const hours = Math.floor(props.durationSeconds / 3600)
  const minutes = Math.floor((props.durationSeconds % 3600) / 60)
  return `${hours}j ${minutes}m`
})

const entryTimeText = computed(() => {
  if (!props.transaction?.entry_time) return '--'
  const d = new Date(props.transaction.entry_time)
  const time = d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })
  const gateName = props.transaction?.gate_in_name || ''
  return `${time} — ${gateName}`
})

const statusText = computed(() => {
  switch (props.paymentState) {
    case 'IDLE': return 'Siap'
    case 'VEHICLE_PRESENT': return 'Kendaraan terdeteksi'
    case 'WAITING_PAYMENT': return 'Menunggu pembayaran'
    case 'TIMEOUT_ALERT': return 'Timeout — butuh intervensi'
    default: return '--'
  }
})

const statusClass = computed(() => {
  if (props.paymentState === 'TIMEOUT_ALERT') return 'status-timeout'
  if (props.paymentState === 'WAITING_PAYMENT') return 'status-waiting'
  return ''
})

const showTimeoutBar = computed(() => {
  return props.paymentState === 'WAITING_PAYMENT' || props.paymentState === 'TIMEOUT_ALERT'
})

const timeoutPercent = computed(() => {
  if (!props.timeoutSeconds) return 0
  return Math.round((props.waitingSeconds / props.timeoutSeconds) * 100)
})

const timeoutBarClass = computed(() => {
  if (timeoutPercent.value >= 100) return 'timeout-flash'
  if (timeoutPercent.value >= 90) return 'timeout-red'
  if (timeoutPercent.value >= 75) return 'timeout-orange'
  return 'timeout-green'
})

function formatWaitingSeconds(seconds) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function formatCurrency(amount) {
  return `Rp ${new Intl.NumberFormat('id-ID').format(amount)}`
}
</script>

<style scoped>
.vehicle-info-card {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.vehicle-details {
  flex: 1;
}

.plate-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.plate-icon {
  font-size: 20px;
}

.plate-number {
  font-size: 24px;
  font-weight: 700;
  font-family: 'Courier New', monospace;
  color: var(--text-primary);
  letter-spacing: 1px;
}

.vehicle-type {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.details-divider {
  height: 1px;
  background: var(--border-color);
  margin: 8px 0;
}

.detail-row {
  display: grid;
  grid-template-columns: 100px 1fr;
  gap: 8px;
  padding: 4px 0;
}

.detail-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.detail-value {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
}

.detail-value.tariff {
  color: var(--accent-green);
  font-weight: 700;
}

.status-timeout {
  color: var(--accent-red) !important;
  font-weight: 700 !important;
}

.status-waiting {
  color: var(--accent-green) !important;
}

.timeout-section {
  margin-top: 12px;
}

.timeout-label {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.timeout-bar-bg {
  height: 8px;
  background: var(--bg-hover);
  border-radius: 4px;
  overflow: hidden;
}

.timeout-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease, background 0.3s ease;
}

.timeout-green {
  background: var(--accent-green);
}

.timeout-orange {
  background: var(--accent-orange);
}

.timeout-red {
  background: var(--accent-red);
}

.timeout-flash {
  background: var(--accent-red);
  animation: flash 1s ease-in-out infinite;
}

@keyframes flash {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
