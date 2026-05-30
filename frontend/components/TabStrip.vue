<template>
  <div class="mb-4 flex gap-1">
    <button
      v-for="tab in tabs"
      :key="tab.key"
      :class="[
        'border-2 border-foreground px-4 py-2 text-sm font-bold uppercase tracking-wide transition-all duration-100',
        modelValue === tab.key
          ? 'bg-primary text-foreground shadow-brutal'
          : 'bg-background text-muted-foreground hover:bg-surface hover:text-foreground shadow-brutal-sm hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-none',
      ]"
      @click="$emit('update:modelValue', tab.key)"
    >
      {{ tab.label }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  tabs: { type: Array, required: true },
  modelValue: { type: String, required: true },
})
defineEmits(['update:modelValue'])
</script>
