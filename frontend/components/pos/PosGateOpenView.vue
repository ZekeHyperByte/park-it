<template>
  <div class="flex h-full flex-col items-center justify-center gap-6 p-6">
    <!-- Change amount (if applicable) -->
    <div v-if="changeAmount > 0" class="text-center space-y-1">
      <div class="text-sm font-black uppercase tracking-wide text-muted-foreground">Kembalian</div>
      <div class="text-5xl font-black text-foreground tabular-nums">{{ formattedChange }}</div>
    </div>

    <!-- Plate reminder -->
    <div v-if="plateNumber" class="text-center">
      <div class="font-mono text-2xl font-black text-muted-foreground tracking-widest">{{ plateNumber }}</div>
    </div>

    <!-- Giant green button -->
    <button
      class="h-40 w-full max-w-md border-4 border-foreground bg-success text-3xl font-black uppercase text-white shadow-brutal-lg transition-all duration-100 hover:translate-x-[4px] hover:translate-y-[4px] hover:shadow-none active:translate-x-[8px] active:translate-y-[8px]"
      @click="$emit('open-gate')"
    >
      Buka Palang
    </button>

    <!-- Space key hint -->
    <div class="text-sm font-medium text-muted-foreground">
      Tekan
      <kbd class="mx-1 inline-flex items-center border-2 border-foreground bg-surface px-2 py-0.5 font-mono text-xs font-bold text-foreground shadow-brutal-sm">Space</kbd>
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
