<template>
  <div class="space-y-6">
    <!-- Greeting bar -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-semibold text-foreground">
          {{ greeting }}, {{ authStore.user?.username || 'Operator' }}
        </h2>
        <p class="mt-1 text-sm text-muted-foreground">{{ formattedDate }}</p>
      </div>
    </div>

    <!-- Hero tile: POS Kiosk -->
    <NuxtLink
      to="/pos"
      class="group flex items-center gap-6 rounded-xl border-l-4 border-l-primary border border-border bg-surface p-6 transition-all hover:border-primary/30 hover:-translate-y-0.5"
    >
      <div class="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
        <svg class="h-7 w-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <path d="M2 10h20" />
          <path d="M12 4v6" />
        </svg>
      </div>
      <div class="flex-1 min-w-0">
        <h3 class="text-lg font-semibold text-foreground">Mulai POS Kiosk</h3>
        <p class="mt-1 text-sm text-muted-foreground">
          Mode layar penuh untuk operasional gate keluar
        </p>
        <div class="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
          <span v-if="posSession.shiftName">
            Shift: <span class="text-foreground font-medium">{{ posSession.shiftName }}</span>
          </span>
          <span>
            Transaksi hari ini: <span class="text-foreground font-medium">{{ posSession.transactionCount }}</span>
          </span>
          <span>
            Kas: <span class="text-foreground font-medium">{{ formatCurrency(posSession.cashCollected) }}</span>
          </span>
        </div>
      </div>
      <div class="shrink-0 text-muted-foreground/40 transition-transform group-hover:translate-x-1">
        <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M9 18l6-6-6-6" />
        </svg>
      </div>
    </NuxtLink>

    <!-- Module grid -->
    <div>
      <h3 class="mb-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground">Modul</h3>
      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <DashboardModuleTile
          v-for="item in visibleModules"
          :key="item.to"
          :title="item.title"
          :description="item.description"
          :icon="item.icon"
          :to="item.to"
          :badge="item.badge"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, markRaw } from 'vue'
import {
  LogIn,
  FileText,
  Users,
  BarChart3,
  Bell,
  Settings,
  Cpu,
} from 'lucide-vue-next'

definePageMeta({
  middleware: 'auth',
  layout: 'default',
})

const authStore = useAuthStore()
const posSession = usePosSessionStore()

// markRaw prevents Vue from making the components reactive (cheap optimisation
// for icon refs that never change).
const allModules = [
  { to: '/gate-in', title: 'Gate In Monitor', description: 'Pantau kendaraan masuk secara real-time', icon: markRaw(LogIn), adminOnly: false },
  { to: '/transaksi', title: 'Transaksi', description: 'Riwayat dan pencarian transaksi parkir', icon: markRaw(FileText), adminOnly: false },
  { to: '/member', title: 'Member', description: 'Kelola kartu member dan langganan', icon: markRaw(Users), adminOnly: false },
  { to: '/report', title: 'Laporan', description: 'Laporan pendapatan dan statistik parkir', icon: markRaw(BarChart3), adminOnly: false },
  { to: '/notification', title: 'Notifikasi', description: 'Peringatan sistem dan notifikasi gate', icon: markRaw(Bell), adminOnly: false },
  { to: '/device', title: 'Perangkat', description: 'Konfigurasi perangkat keras dan gate', icon: markRaw(Cpu), adminOnly: true },
  { to: '/setting', title: 'Pengaturan', description: 'Pengaturan sistem, tarif, dan shift', icon: markRaw(Settings), adminOnly: true },
]

const visibleModules = computed(() =>
  allModules.filter((m) => !m.adminOnly || authStore.isAdmin)
)

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 11) return 'Selamat pagi'
  if (hour < 15) return 'Selamat siang'
  if (hour < 18) return 'Selamat sore'
  return 'Selamat malam'
})

const formattedDate = computed(() => {
  return new Date().toLocaleDateString('id-ID', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
})

function formatCurrency(value) {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
  }).format(value || 0)
}

onMounted(async () => {
  await posSession.loadShiftSummary()
})
</script>
