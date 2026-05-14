<template>
  <div class="space-y-2">
    <div
      v-for="check in checks"
      :key="check.name"
      class="flex items-center justify-between gap-3 rounded-md border border-border bg-background px-3 py-2"
    >
      <div class="min-w-0">
        <p class="truncate text-sm font-medium text-foreground">{{ check.name }}</p>
        <p v-if="check.message" class="truncate text-xs text-muted-foreground">{{ check.message }}</p>
      </div>
      <span
        :class="[
          'inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
          tone(check.status),
        ]"
      >
        <span :class="dotClass(check.status)" class="h-1.5 w-1.5 rounded-full" />
        {{ statusLabel(check.status) }}
      </span>
    </div>

    <p v-if="!checks.length" class="text-sm text-muted-foreground">
      Tidak ada pemeriksaan yang dijalankan.
    </p>
  </div>
</template>

<script setup>
defineProps({
  checks: { type: Array, default: () => [] },
})

function tone(status) {
  if (status === 'PASS') return 'bg-success/15 text-success'
  if (status === 'WARN') return 'bg-warning/15 text-warning'
  if (status === 'FAIL') return 'bg-destructive/15 text-destructive'
  return 'bg-muted text-muted-foreground'
}

function dotClass(status) {
  if (status === 'PASS') return 'bg-success'
  if (status === 'WARN') return 'bg-warning'
  if (status === 'FAIL') return 'bg-destructive'
  return 'bg-muted-foreground/50'
}

function statusLabel(status) {
  if (status === 'PASS') return 'Lulus'
  if (status === 'WARN') return 'Perhatian'
  if (status === 'FAIL') return 'Gagal'
  return status
}
</script>
