<template>
  <div class="flex h-full flex-col items-center justify-center gap-6 p-6">
    <!-- Change amount (if applicable) -->
    <div v-if="changeAmount > 0" class="text-center space-y-1">
      <div class="text-sm text-muted-foreground uppercase tracking-wide">Kembalian</div>
      <div class="text-5xl font-black text-foreground tabular-nums">{{ formattedChange }}</div>
    </div>

    <!-- Plate reminder -->
    <div v-if="plateNumber" class="text-center">
      <div class="font-mono text-2xl font-bold text-muted-foreground tracking-widest">{{ plateNumber }}</div>
    </div>

    <!-- Giant green button -->
    <button
      class="h-40 w-full max-w-md rounded-3xl bg-success text-3xl font-black text-white shadow-[0_0_60px_rgba(34,197,94,0.3)] transition-all hover:shadow-[0_0_80px_rgba(34,197,94,0.5)] hover:scale-[1.02] active:scale-[0.98]"
      @click="$emit('open-gate')"
    >
      Buka Palang
    </button>

    <!-- Space key hint -->
    <div class="text-sm text-muted-foreground">
      Tekan
      <kbd class="mx-1 inline-flex items-center rounded bg-surface border border-border px-2 py-0.5 font-mono text-xs font-medium text-foreground">Space</kbd>
      untuk buka palang
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useFormatters } from '~/composables/useFormatters'

const props = defineProps({
  changeAmount: { type: Number, default: 0 },
  plateNumber: { type: String, default: '' },
})

defineEmits(['open-gate'])

const { formatCurrency } = useFormatters()

const formattedChange = computed(() => formatCurrency(props.changeAmount))
</script>
