<script setup lang="ts">
import type { HTMLAttributes } from "vue"
import { cn } from "@/lib/utils"

const props = defineProps<{
  class?: HTMLAttributes["class"]
  variant?: "default" | "success" | "warning" | "destructive" | "info"
  pulse?: boolean
}>()

const variantClasses: Record<string, string> = {
  default: "bg-primary text-foreground",
  success: "bg-success text-white",
  warning: "bg-warning text-foreground",
  destructive: "bg-destructive text-white",
  info: "bg-info text-white",
}
</script>

<template>
  <span
    :class="
      cn(
        'inline-flex items-center gap-2 border-2 border-foreground px-3 py-1 text-xs font-bold uppercase tracking-wide shadow-brutal-sm',
        variantClasses[variant || 'default'],
        props.class,
      )
    "
  >
    <span
      v-if="pulse"
      class="h-2 w-2 bg-current animate-pulse"
    />
    <slot />
  </span>
</template>
