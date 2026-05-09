<template>
  <div class="flex items-center justify-between w-full">
    <!-- Left: Keyboard shortcuts -->
    <div class="flex items-center gap-3">
      <template v-if="!isIdle">
        <div
          v-for="shortcut in shortcuts"
          :key="shortcut.key"
          class="flex items-center gap-1.5"
          :class="shortcut.active ? 'opacity-100' : 'opacity-30'"
        >
          <kbd
            :class="[
              'inline-flex h-6 min-w-[1.75rem] items-center justify-center rounded px-1.5 font-mono text-[11px] font-medium',
              shortcut.active
                ? 'bg-surface border border-border text-foreground'
                : 'bg-surface/50 text-muted-foreground',
            ]"
          >
            {{ shortcut.key }}
          </kbd>
          <span class="text-xs text-muted-foreground">{{ shortcut.label }}</span>
        </div>
      </template>
      <template v-else>
        <span v-if="gateName || shiftName" class="text-xs text-muted-foreground">
          <span v-if="gateName" class="font-medium text-foreground">{{ gateName }}</span>
          <span v-if="gateName && shiftName" class="mx-1.5 text-border">|</span>
          <span v-if="shiftName">{{ shiftName }}</span>
          <span class="mx-1.5 text-border">|</span>
        </span>
        <span class="text-xs text-muted-foreground/50">
          Scan barcode untuk memulai
        </span>
      </template>
    </div>

    <!-- Center: State indicator -->
    <div class="flex items-center gap-2">
      <span
        v-if="showPulse"
        :class="['h-2 w-2 rounded-full animate-pulse', stateDotColor]"
      />
      <span :class="['text-sm font-medium', stateColor]">{{ stateText }}</span>
    </div>

    <!-- Right: Clock -->
    <div class="font-mono text-sm text-muted-foreground tabular-nums">{{ clock }}</div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  paymentState: { type: String, default: 'IDLE' },
  emoneyState: { type: String, default: 'IDLE' },
  awaitingGateOpen: { type: Boolean, default: false },
  canPayCash: { type: Boolean, default: false },
  canPayRfid: { type: Boolean, default: false },
  canPayEmoney: { type: Boolean, default: false },
  gateName: { type: String, default: '' },
  shiftName: { type: String, default: '' },
})

const clock = ref('')
let clockTimer = null

const shortcuts = computed(() => [
  { key: 'F1', label: 'Cash', active: props.canPayCash },
  { key: 'F2', label: 'RFID', active: props.canPayRfid },
  { key: 'F3', label: 'E-Money', active: props.canPayEmoney },
  { key: 'Space', label: 'Buka Palang', active: props.awaitingGateOpen },
  { key: 'Esc', label: 'Batal', active: true },
])

const isIdle = computed(() =>
  props.paymentState === 'IDLE' &&
  props.emoneyState === 'IDLE' &&
  !props.awaitingGateOpen &&
  !props.canPayCash &&
  !props.canPayRfid &&
  !props.canPayEmoney,
)

const showPulse = computed(() =>
  props.awaitingGateOpen ||
  props.emoneyState === 'PROCESSING' ||
  props.paymentState === 'WAITING_PAYMENT'
)

const stateDotColor = computed(() => {
  if (props.awaitingGateOpen) return 'bg-success'
  if (props.emoneyState === 'PROCESSING') return 'bg-warning'
  if (props.paymentState === 'TIMEOUT_ALERT') return 'bg-destructive'
  return 'bg-primary'
})

const stateText = computed(() => {
  if (props.awaitingGateOpen) return 'Tekan Space untuk buka palang'
  if (props.emoneyState === 'PROCESSING') return 'E-Money: Memproses...'
  if (props.emoneyState === 'SUCCESS') return 'E-Money: Berhasil'
  if (props.paymentState === 'TIMEOUT_ALERT') return 'Timeout!'
  if (props.paymentState === 'WAITING_PAYMENT') return 'Menunggu pembayaran'
  if (props.paymentState === 'VEHICLE_PRESENT') return 'Kendaraan terdeteksi'
  return 'Menunggu kendaraan...'
})

const stateColor = computed(() => {
  if (props.awaitingGateOpen) return 'text-success'
  if (props.emoneyState === 'PROCESSING') return 'text-warning'
  if (props.emoneyState === 'SUCCESS') return 'text-success'
  if (props.paymentState === 'TIMEOUT_ALERT') return 'text-destructive'
  return 'text-muted-foreground'
})

function updateClock() {
  clock.value = new Date().toLocaleTimeString('id-ID', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

onMounted(() => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
})
</script>
