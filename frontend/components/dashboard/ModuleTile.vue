<template>
  <NuxtLink
    :to="to"
    class="group flex items-start gap-4 border-2 border-foreground bg-surface p-5 shadow-brutal transition-all duration-100 hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none"
  >
    <div class="flex h-10 w-10 shrink-0 items-center justify-center border-2 border-foreground bg-primary text-foreground">
      <component
        :is="icon"
        v-if="typeof icon !== 'string'"
        class="h-5 w-5"
        :stroke-width="2"
      />
      <span v-else class="h-5 w-5" v-html="icon" />
    </div>
    <div class="min-w-0 flex-1">
      <div class="flex items-center gap-2">
        <h3 class="text-sm font-black uppercase tracking-wide text-foreground">{{ title }}</h3>
        <span
          v-if="badge"
          class="border-2 border-foreground bg-destructive px-2 py-0.5 text-xs font-bold text-white shadow-brutal-sm"
        >
          {{ badge }}
        </span>
      </div>
      <p class="mt-1 text-xs font-medium text-muted-foreground leading-relaxed">{{ description }}</p>
    </div>
  </NuxtLink>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, required: true },
  // Vue component (preferred) or SVG string (legacy)
  icon: { type: [Object, Function, String], required: true },
  to: { type: String, required: true },
  badge: { type: [String, Number], default: null },
})
</script>
