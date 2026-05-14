<template>
  <div :class="['space-y-1.5', props.class]">
    <label v-if="label" class="text-sm font-medium text-foreground">
      {{ label }}
      <span v-if="required" class="text-destructive">*</span>
    </label>
    <slot />
    <p v-if="error" class="text-xs text-destructive">{{ error }}</p>
    <p v-else-if="helper" class="text-xs text-muted-foreground">{{ helper }}</p>
  </div>
</template>

<script setup>
const props = defineProps({
  label: { type: String, default: '' },
  helper: { type: String, default: '' },
  error: { type: String, default: '' },
  required: { type: Boolean, default: false },
  class: { type: String, default: '' },
})
</script>
