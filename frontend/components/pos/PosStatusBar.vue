<template>
  <div class="flex items-center justify-between w-full">
    <!-- Left: Gate identity + connection -->
    <div class="flex items-center gap-2.5">
      <span class="text-sm font-semibold text-foreground">{{ gateName }}</span>
      <span class="flex items-center gap-1.5">
        <span
          :class="[
            'h-2 w-2 rounded-full',
            wsConnected ? 'bg-success animate-pulse' : 'bg-destructive',
          ]"
        />
        <span :class="['text-xs font-medium', wsConnected ? 'text-success' : 'text-destructive']">
          {{ wsConnected ? 'Online' : 'Offline' }}
        </span>
      </span>
    </div>

    <!-- Center: Hardware indicators -->
    <div class="flex items-center gap-3">
      <div
        v-for="item in indicators"
        :key="item.label"
        class="flex items-center gap-1.5"
        :title="`${item.label}: ${item.statusText}`"
      >
        <span
          :class="[
            'h-2 w-2 rounded-full',
            item.ok ? 'bg-success' : item.warn ? 'bg-warning' : 'bg-destructive',
          ]"
        />
        <span class="text-xs text-muted-foreground">{{ item.label }}</span>
      </div>
    </div>

    <!-- Right: Session stats + clock -->
    <div class="flex items-center gap-3 text-sm">
      <span class="text-muted-foreground">
        <span class="font-medium text-foreground">{{ transactionCount }}</span> tx
      </span>
      <span class="text-border">|</span>
      <span class="font-medium text-foreground">{{ formattedCash }}</span>
      <span class="text-border">|</span>
      <span class="font-mono text-xs text-muted-foreground tabular-nums">{{ clock }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useFormatters } from '~/composables/useFormatters'

const props = defineProps({
  gateName: { type: String, default: '--' },
  wsConnected: { type: Boolean, default: false },
  boothConnected: { type: Boolean, default: false },
  hardwareStatus: { type: Object, default: () => ({}) },
  transactionCount: { type: Number, default: 0 },
  cashCollected: { type: Number, default: 0 },
})

const { formatCurrency } = useFormatters()

const clock = ref('')
let clockTimer = null

const formattedCash = computed(() => formatCurrency(props.cashCollected))

const indicators = computed(() => [
  {
    label: 'Booth',
    ok: props.boothConnected,
    warn: false,
    statusText: props.boothConnected ? 'connected' : 'disconnected',
  },
  {
    label: 'E-Money',
    ok: props.hardwareStatus?.emoney?.status === 'ready',
    warn: props.hardwareStatus?.emoney?.status === 'stale',
    statusText: props.hardwareStatus?.emoney?.status || 'unknown',
  },
  {
    label: 'Printer',
    ok: props.hardwareStatus?.printer?.status === 'online',
    warn: props.hardwareStatus?.printer?.status === 'stale',
    statusText: props.hardwareStatus?.printer?.status || 'unknown',
  },
])

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
