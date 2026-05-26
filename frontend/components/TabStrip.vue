<template>
  <div class="mb-4 flex gap-1 border-b border-border">
    <button
      v-for="tab in tabs"
      :key="tab.key"
      :class="[
        'px-4 py-2 text-sm font-medium transition-colors -mb-px',
        modelValue === tab.key
          ? 'border-b-2 border-primary text-primary'
          : 'text-muted-foreground hover:text-foreground',
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
