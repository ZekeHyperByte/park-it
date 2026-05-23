<template>
  <div class="flex items-center justify-between w-full">
    <!-- Left: Keyboard shortcuts (always visible) -->
    <div class="flex items-center gap-4">
      <span v-if="gateName || shiftName" class="text-base text-muted-foreground">
        <span v-if="gateName" class="font-semibold text-foreground">{{ gateName }}</span>
        <span v-if="gateName && shiftName" class="mx-2 text-border">|</span>
        <span v-if="shiftName">{{ shiftName }}</span>
        <span class="mx-2 text-border">|</span>
      </span>
      <span v-if="isMixedLane && activeVehicleTypeName" class="flex items-center gap-2 mr-2">
        <span class="rounded bg-primary/10 px-3 py-1 text-base font-semibold text-primary">{{ activeVehicleTypeName }}</span>
      </span>
      <div
        v-for="shortcut in shortcuts"
        :key="shortcut.key"
        class="flex items-center gap-2"
        :class="shortcut.active ? 'opacity-100' : 'opacity-30'"
      >
        <kbd
          :class="[
            'inline-flex h-9 min-w-[2.5rem] items-center justify-center rounded px-2 font-mono text-sm font-semibold',
            shortcut.active
              ? 'bg-surface border border-border text-foreground'
              : 'bg-surface/50 text-muted-foreground',
          ]"
        >
          {{ shortcut.key }}
        </kbd>
        <span class="text-base text-muted-foreground">{{ shortcut.label }}</span>
      </div>
    </div>

  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  paymentState: { type: String, default: 'IDLE' },
  emoneyState: { type: String, default: 'IDLE' },
  awaitingGateOpen: { type: Boolean, default: false },
  canPayCash: { type: Boolean, default: false },
  gateName: { type: String, default: '' },
  shiftName: { type: String, default: '' },
  isMixedLane: { type: Boolean, default: false },
  activeVehicleTypeName: { type: String, default: null },
})

const shortcuts = computed(() => {
  const base = [
    { key: 'F1', label: 'Tunai', active: props.canPayCash },
    { key: 'Space', label: 'Buka Palang', active: props.awaitingGateOpen },
    { key: 'Esc', label: 'Batal', active: true },
  ]
  if (props.isMixedLane) {
    base.unshift(
      { key: 'C', label: 'Mobil', active: true },
      { key: 'M', label: 'Motor', active: true },
    )
  }
  return base
})

</script>
