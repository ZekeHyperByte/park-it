<template>
  <div class="flex-1 text-center">
    <div class="text-[10px] uppercase tracking-wider text-muted-foreground">{{ label }}</div>
    <div class="text-base font-medium text-foreground tabular-nums">
      {{ value || '--' }}
    </div>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: String, default: null },
})
</script>
