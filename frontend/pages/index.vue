<template>
  <div class="space-y-6">
    <!-- Greeting bar -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-black uppercase tracking-wide text-foreground">
          {{ greeting }}, {{ authStore.user?.full_name || authStore.user?.username || 'Pengguna' }}
        </h2>
        <p class="mt-1 text-sm font-medium text-muted-foreground">{{ formattedDate }}</p>
      </div>
    </div>

    <!-- Live status strip -->
    <div class="flex items-center gap-4 border-2 border-foreground bg-surface px-4 py-3 text-sm shadow-brutal">
      <div class="flex items-center gap-2">
        <span
          :class="['h-3 w-3 border border-foreground', activeCount > 0 ? 'bg-success animate-pulse' : 'bg-muted']"
        />
        <span class="font-bold uppercase text-foreground">Kendaraan aktif:</span>
        <span class="font-black text-lg text-foreground">{{ loadingStatus ? '...' : activeCount }}</span>
      </div>
      <div class="h-6 w-0.5 bg-foreground" />
      <div class="flex items-center gap-2">
        <span
          :class="['h-3 w-3 border border-foreground', unresolvedCount > 0 ? 'bg-warning animate-pulse' : 'bg-muted']"
        />
        <span class="font-bold uppercase text-foreground">Unresolved e-money:</span>
        <span :class="['font-black text-lg', unresolvedCount > 0 ? 'text-warning' : 'text-foreground']">
          {{ loadingStatus ? '...' : unresolvedCount }}
        </span>
      </div>
      <div class="h-6 w-0.5 bg-foreground" />
      <div class="flex items-center gap-2">
        <span class="font-bold uppercase text-foreground">Gate aktif:</span>
        <span class="font-black text-lg text-foreground">{{ websiteStore.activeGateOuts.length + websiteStore.activeGateIns.length }}</span>
      </div>
    </div>

    <!-- Hero tile: POS Kiosk -->
    <NuxtLink
      to="/pos"
      class="group flex items-center gap-6 border-4 border-foreground bg-primary p-6 shadow-brutal-lg transition-all duration-100 hover:translate-x-[4px] hover:translate-y-[4px] hover:shadow-none"
    >
      <div class="flex h-14 w-14 shrink-0 items-center justify-center border-2 border-foreground bg-background text-foreground">
        <svg class="h-7 w-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <path d="M2 10h20" />
          <path d="M12 4v6" />
        </svg>
      </div>
      <div class="flex-1 min-w-0">
        <h3 class="text-2xl font-black uppercase tracking-wide text-foreground">Mulai POS Kiosk</h3>
        <p class="mt-1 text-sm font-medium text-foreground/80">
          Mode layar penuh untuk operasional gate keluar
        </p>
        <div class="mt-3 flex items-center gap-4 text-xs font-bold uppercase text-foreground">
          <span v-if="posSession.shiftName">
            Shift: <span class="bg-background border-2 border-foreground px-2 py-0.5 shadow-brutal-sm">{{ posSession.shiftName }}</span>
          </span>
          <span>
            Transaksi: <span class="bg-background border-2 border-foreground px-2 py-0.5 shadow-brutal-sm">{{ posSession.transactionCount }}</span>
          </span>
          <span>
            Kas: <span class="bg-background border-2 border-foreground px-2 py-0.5 shadow-brutal-sm">{{ formatCurrency(posSession.cashCollected) }}</span>
          </span>
        </div>
      </div>
      <div class="shrink-0 text-foreground transition-transform group-hover:translate-x-2">
        <svg class="h-8 w-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round">
          <path d="M9 18l6-6-6-6" />
        </svg>
      </div>
    </NuxtLink>

    <!-- Module grid -->
    <div>
      <h3 class="mb-4 text-sm font-black uppercase tracking-wider text-foreground border-b-2 border-foreground pb-2">Modul</h3>
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
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
import { ref, computed, onMounted, markRaw } from 'vue'
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
const websiteStore = useWebsiteStore()
const { fetchApi } = useApi()

const loadingStatus = ref(true)
const activeCount = ref(0)
const unresolvedCount = ref(0)

const allModules = [
  { to: '/gate-in', title: 'Gate In Monitor', description: 'Pantau kendaraan masuk secara real-time', icon: markRaw(LogIn), adminOnly: false, badge: null },
  { to: '/transaksi', title: 'Transaksi', description: 'Riwayat dan pencarian transaksi parkir', icon: markRaw(FileText), adminOnly: false, badge: null },
  { to: '/member', title: 'Member', description: 'Kelola kartu member dan langganan', icon: markRaw(Users), adminOnly: false, badge: null },
  { to: '/report', title: 'Laporan', description: 'Laporan pendapatan dan statistik parkir', icon: markRaw(BarChart3), adminOnly: false, badge: null },
  { to: '/notification', title: 'Notifikasi', description: 'Peringatan sistem dan notifikasi gate', icon: markRaw(Bell), adminOnly: false, badge: null },
  { to: '/device', title: 'Perangkat', description: 'Konfigurasi perangkat keras dan gate', icon: markRaw(Cpu), adminOnly: true, badge: null },
  { to: '/setting', title: 'Pengaturan', description: 'Pengaturan sistem, tarif, dan shift', icon: markRaw(Settings), adminOnly: true, badge: null },
]

const modules = ref(allModules.map((m) => ({ ...m })))

const visibleModules = computed(() =>
  modules.value.filter((m) => !m.adminOnly || authStore.isAdmin)
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

async function loadStatus() {
  loadingStatus.value = true
  try {
    const [activeRes, unresolvedRes] = await Promise.all([
      fetchApi('/api/transactions?status=ACTIVE&limit=1').catch(() => null),
      fetchApi('/api/transactions?status=LOST_CONTACT&limit=1').catch(() => null),
    ])
    activeCount.value = activeRes?.total ?? 0
    unresolvedCount.value = unresolvedRes?.total ?? 0

    // Badge on notification tile when there are unresolved e-money transactions
    if (unresolvedCount.value > 0) {
      const notifModule = modules.value.find((m) => m.to === '/notification')
      if (notifModule) notifModule.badge = unresolvedCount.value
    }
  } finally {
    loadingStatus.value = false
  }
}

onMounted(async () => {
  await Promise.all([
    posSession.loadShiftSummary(),
    websiteStore.loadAll(),
    loadStatus(),
  ])
})
</script>
