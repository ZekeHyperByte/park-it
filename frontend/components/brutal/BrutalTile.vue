<script setup lang="ts">
import type { HTMLAttributes } from "vue"
import { cn } from "@/lib/utils"

const props = defineProps<{
  class?: HTMLAttributes["class"]
  to?: string
  active?: boolean
}>()
</script>

<template>
  <NuxtLink
    v-if="to"
    :to="to"
    :class="
      cn(
        'block border-2 border-foreground bg-surface p-5 shadow-brutal transition-all duration-100 hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none',
        active && 'bg-primary',
        props.class,
      )
    "
  >
    <slot />
  </NuxtLink>
  <div
    v-else
    :class="
      cn(
        'border-2 border-foreground bg-surface p-5 shadow-brutal transition-all duration-100 hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none',
        active && 'bg-primary',
        props.class,
      )
    "
  >
    <slot />
  </div>
</template>
