<template>
  <nav role="navigation" aria-label="Setup steps" class="flex flex-wrap items-center gap-2 sm:gap-3">
    <template v-for="(step, idx) in steps" :key="step.key">
      <div class="flex flex-col items-center gap-1">
        <button
          type="button"
          :aria-current="idx === currentIndex ? 'step' : undefined"
          :disabled="!canNavigate(idx)"
          :class="[
            'flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold transition-colors',
            idx < currentIndex && 'bg-success/90 text-white border-success focus-visible:ring-success',
            idx === currentIndex && 'bg-primary text-primary-foreground border-primary ring-4 ring-primary/20',
            idx > currentIndex && 'bg-muted text-muted-foreground border-border',
            canNavigate(idx) ? 'cursor-pointer hover:opacity-90' : 'cursor-not-allowed opacity-70',
          ]"
          @click="onClick(idx)"
        >
          <svg v-if="idx < currentIndex" class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          <span v-else>{{ idx + 1 }}</span>
        </button>
        <span
          :class="[
            'hidden text-xs sm:block',
            idx === currentIndex ? 'font-medium text-foreground' : 'text-muted-foreground',
          ]"
        >
          {{ step.label }}
        </span>
      </div>
      <div
        v-if="idx < steps.length - 1"
        :class="[
          'mt-[-12px] h-px flex-1 min-w-4 max-w-12',
          idx < currentIndex ? 'bg-success/60' : 'bg-border',
        ]"
      />
    </template>
  </nav>
</template>

<script setup>
const props = defineProps({
  steps: { type: Array, required: true },
  currentIndex: { type: Number, default: 0 },
})

const emit = defineEmits(['navigate'])

function canNavigate(idx) {
  return idx <= props.currentIndex
}

function onClick(idx) {
  if (canNavigate(idx)) emit('navigate', idx)
}
</script>
