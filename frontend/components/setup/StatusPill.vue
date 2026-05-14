<template>
  <span
    :class="[
      'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium',
      classes[status] || classes.idle,
    ]"
    role="status"
    aria-live="polite"
  >
    <span :class="['h-1.5 w-1.5 rounded-full', dotClasses[status] || dotClasses.idle, status === 'testing' && 'animate-pulse']" />
    <span>{{ label || defaultLabels[status] || status }}</span>
  </span>
</template>

<script setup>
const props = defineProps({
  status: {
    type: String,
    default: 'idle',
    validator: (v) => ['online', 'offline', 'testing', 'warning', 'idle'].includes(v),
  },
  label: { type: String, default: '' },
})

const classes = {
  online: 'bg-success/15 text-success border-success/30',
  offline: 'bg-destructive/15 text-destructive border-destructive/30',
  testing: 'bg-primary/15 text-primary border-primary/30',
  warning: 'bg-warning/15 text-warning border-warning/30',
  idle: 'bg-muted text-muted-foreground border-border',
}

const dotClasses = {
  online: 'bg-success',
  offline: 'bg-destructive',
  testing: 'bg-primary',
  warning: 'bg-warning',
  idle: 'bg-muted-foreground/50',
}

const defaultLabels = {
  online: 'Terhubung',
  offline: 'Tidak Terhubung',
  testing: 'Menguji...',
  warning: 'Peringatan',
  idle: 'Idle',
}
</script>
