<script setup lang="ts">
import type { TooltipRootEmits, TooltipRootProps } from "reka-ui"
import { TooltipRoot } from "reka-ui"

const props = defineProps<TooltipRootProps>()
const emits = defineEmits<TooltipRootEmits>()
</script>

<template>
  <TooltipRoot :delay-duration="props.delayDuration" :disable-hoverable-content="props.disableHoverableContent">
    <slot />
  </TooltipRoot>
</template>
