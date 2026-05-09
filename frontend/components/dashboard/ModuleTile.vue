<template>
  <NuxtLink
    :to="to"
    class="group flex items-start gap-4 rounded-xl border border-border bg-surface p-5 transition-all hover:border-primary/30 hover:-translate-y-0.5"
  >
    <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
      <!-- Accept either a Vue component (e.g. lucide-vue-next icon) or a raw
           SVG string for legacy callers. -->
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
        <h3 class="text-sm font-semibold text-foreground">{{ title }}</h3>
        <span
          v-if="badge"
          class="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
        >
          {{ badge }}
        </span>
      </div>
      <p class="mt-1 text-xs text-muted-foreground leading-relaxed">{{ description }}</p>
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
