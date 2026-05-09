<script setup lang="ts">
import type { DialogRootEmits, DialogRootProps } from "reka-ui"
import { DialogRoot } from "reka-ui"

const props = defineProps<DialogRootProps>()
const emits = defineEmits<DialogRootEmits>()
</script>

<template>
  <DialogRoot :open="props.open" :modal="props.modal" @update:open="emits('update:open', $event)">
    <slot />
  </DialogRoot>
</template>
