<script setup lang="ts">
import type { HTMLAttributes } from "vue"
import { cn } from "@/lib/utils"

const props = defineProps<{
  class?: HTMLAttributes["class"]
  hover?: boolean
}>()
</script>

<template>
  <div
    :class="
      cn(
        'border-2 border-foreground bg-surface shadow-brutal p-5',
        hover && 'transition-all duration-100 hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none',
        props.class,
      )
    "
  >
    <slot />
  </div>
</template>
