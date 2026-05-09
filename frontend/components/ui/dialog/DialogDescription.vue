<script setup lang="ts">
import type { DialogDescriptionProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { DialogDescription } from "reka-ui"
import { cn } from "@/lib/utils"

const props = defineProps<DialogDescriptionProps & { class?: HTMLAttributes["class"] }>()

function getDescProps() {
  const { class: _, ...rest } = props
  return rest
}
</script>

<template>
  <DialogDescription
    v-bind="getDescProps()"
    :class="cn('text-sm text-muted-foreground', props.class)"
  >
    <slot />
  </DialogDescription>
</template>
