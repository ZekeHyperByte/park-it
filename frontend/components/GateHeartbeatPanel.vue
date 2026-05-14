<template>
  <section class="space-y-3">
    <header class="flex items-baseline justify-between">
      <h2 class="text-base font-semibold text-foreground">Status Gerbang</h2>
      <span class="text-xs text-muted-foreground">
        <template v-if="lastFetch">Diperbarui {{ lastFetchLabel }}</template>
      </span>
    </header>

    <div v-if="error" class="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
      {{ error }}
    </div>

    <div v-else-if="loading && gates.length === 0" class="text-sm text-muted-foreground">
      Memuat…
    </div>

    <div v-else class="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
      <article
        v-for="g in gates"
        :key="g.code"
        :class="[
          'rounded-lg border bg-surface p-3 transition-colors',
          cardBorder(g),
        ]"
      >
        <header class="flex items-start justify-between gap-2">
          <div>
            <p class="text-xs font-mono text-muted-foreground">{{ g.code }}</p>
            <p class="text-sm font-semibold text-foreground">{{ g.direction === 'IN' ? 'Masuk' : 'Keluar' }}</p>
          </div>
          <span :class="['text-lg leading-none', dotColor(g)]">●</span>
        </header>

        <dl class="mt-2 space-y-1 text-xs">
          <div class="flex justify-between">
            <dt class="text-muted-foreground">Daemon</dt>
            <dd class="font-medium text-foreground">{{ g.online ? 'Online' : 'Offline' }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-muted-foreground">Controller</dt>
            <dd class="font-medium text-foreground">{{ g.online ? (g.controller_ok ? 'OK' : 'Bermasalah') : '—' }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-muted-foreground">State</dt>
            <dd class="font-mono text-foreground">{{ g.state || '—' }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-muted-foreground">Last seen</dt>
            <dd class="font-mono text-foreground">{{ lastSeenLabel(g) }}</dd>
          </div>
        </dl>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  pollIntervalMs: { type: Number, default: 5000 },
})

const { fetchApi } = useApi()

const gates = ref([])
const loading = ref(false)
const error = ref('')
const lastFetch = ref(null)
const now = ref(Date.now())

let pollTimer = null
let clockTimer = null

async function refresh() {
  loading.value = true
  try {
    const data = await fetchApi('/api/gates/status/heartbeat')
    gates.value = data?.gates || []
    error.value = ''
    lastFetch.value = Date.now()
  } catch (e) {
    error.value = e?.message || 'Gagal memuat status'
  } finally {
    loading.value = false
  }
}

function cardBorder(g) {
  if (!g.online) return 'border-destructive/40'
  if (!g.controller_ok) return 'border-warning/40'
  return 'border-success/40'
}

function dotColor(g) {
  if (!g.online) return 'text-destructive'
  if (!g.controller_ok) return 'text-warning'
  return 'text-success'
}

function lastSeenLabel(g) {
  if (!g.last_seen) return '—'
  const t = new Date(g.last_seen).getTime()
  const sec = Math.max(0, Math.floor((now.value - t) / 1000))
  if (sec < 60) return `${sec}s lalu`
  return `${Math.floor(sec / 60)}m lalu`
}

const lastFetchLabel = computed(() => {
  if (!lastFetch.value) return ''
  const sec = Math.max(0, Math.floor((now.value - lastFetch.value) / 1000))
  return `${sec}s lalu`
})

onMounted(() => {
  refresh()
  pollTimer = setInterval(refresh, props.pollIntervalMs)
  clockTimer = setInterval(() => { now.value = Date.now() }, 1000)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
  if (clockTimer) clearInterval(clockTimer)
})
</script>
