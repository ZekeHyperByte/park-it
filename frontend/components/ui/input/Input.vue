<script setup lang="ts">
import { computed } from "vue"
import type { HTMLAttributes } from "vue"
import { cn } from "@/lib/utils"

const props = defineProps<{
  defaultValue?: string | number
  modelValue?: string | number
  class?: HTMLAttributes["class"]
}>()

const emits = defineEmits<{
  (e: "update:modelValue", payload: string | number): void
}>()

const modelValue = computed({
  get: () => props.modelValue ?? props.defaultValue,
  set: (value) => emits("update:modelValue", value),
})
</script>

<template>
  <input v-model="modelValue" :class="cn('flex h-10 w-full border-2 border-foreground bg-background px-4 py-2 text-sm font-medium placeholder:text-muted-foreground placeholder:font-normal transition-all duration-100 focus-visible:outline-none focus-visible:shadow-brutal-sm focus-visible:translate-x-[2px] focus-visible:translate-y-[2px] disabled:cursor-not-allowed disabled:opacity-40 file:border-0 file:bg-transparent file:text-foreground file:text-sm file:font-medium', props.class)">
</template>
