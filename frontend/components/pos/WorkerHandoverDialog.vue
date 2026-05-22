<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
    <div class="w-full max-w-md rounded-xl border border-border bg-background p-6 shadow-2xl">

      <!-- OUTGOING: step 1 — current worker confirms leaving -->
      <template v-if="internalStep === 'outgoing'">
        <div class="mb-6 text-center">
          <div class="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-warning/10">
            <svg class="h-6 w-6 text-warning" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
          </div>
          <h2 class="text-lg font-semibold text-foreground">Selesai Shift</h2>
          <p class="mt-1 text-sm text-muted-foreground">
            Masukkan PIN Anda untuk mengkonfirmasi bahwa Anda selesai bertugas
          </p>
        </div>

        <div class="flex items-center gap-3 rounded-lg border border-border bg-surface px-4 py-3 mb-4">
          <div class="flex h-8 w-8 items-center justify-center rounded-full bg-warning/20 text-warning font-bold text-sm">
            {{ initials(currentWorker) }}
          </div>
          <div>
            <p class="font-medium text-foreground">{{ currentWorker?.full_name || currentWorker?.username }}</p>
            <p class="text-xs text-muted-foreground">Petugas aktif saat ini</p>
          </div>
        </div>

        <div class="mb-4">
          <label class="block text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">PIN Anda (4 digit)</label>
          <input
            ref="outgoingPinInput"
            v-model="outgoingPin"
            type="password"
            inputmode="numeric"
            maxlength="4"
            placeholder="••••"
            class="w-full rounded-lg border border-border bg-surface px-4 py-3 text-center text-2xl tracking-[0.5em] text-foreground placeholder:text-muted-foreground/40 focus:border-primary focus:outline-none"
            @keydown.enter="submitOutgoing"
          />
        </div>

        <div v-if="earlyLeave" class="mb-4">
          <label class="block text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">Alasan pergi lebih awal</label>
          <input
            v-model="endReason"
            type="text"
            maxlength="255"
            placeholder="Isi alasan..."
            class="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
          />
        </div>

        <div v-if="errorMsg" class="mb-3 rounded-lg bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
          {{ errorMsg }}
        </div>

        <div class="flex gap-2">
          <button
            class="flex-1 rounded-lg border border-border px-4 py-3 text-sm font-medium text-foreground hover:bg-surface transition-colors"
            @click="$emit('cancel')"
          >
            Batal
          </button>
          <button
            :disabled="outgoingPin.length < 4 || isLoading"
            class="flex-1 rounded-lg bg-warning px-4 py-3 text-sm font-semibold text-warning-foreground transition-opacity disabled:opacity-40"
            @click="submitOutgoing"
          >
            <span v-if="isLoading">Memproses...</span>
            <span v-else>Konfirmasi Selesai</span>
          </button>
        </div>
      </template>

      <!-- PENDING: waiting for incoming worker -->
      <template v-else-if="internalStep === 'pending'">
        <div class="mb-6 text-center">
          <div class="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <svg class="h-6 w-6 text-primary animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 12a9 9 0 1 1-6.219-8.56" />
            </svg>
          </div>
          <h2 class="text-lg font-semibold text-foreground">Menunggu Petugas Pengganti</h2>
          <p class="mt-1 text-sm text-muted-foreground">
            Petugas pengganti harus konfirmasi sebelum Anda dapat meninggalkan pos
          </p>
        </div>

        <!-- Incoming: pick + PIN -->
        <div class="space-y-3">
          <p class="text-xs font-medium uppercase tracking-wider text-muted-foreground">Petugas pengganti</p>
          <div class="grid grid-cols-2 gap-2">
            <button
              v-for="worker in availableWorkers"
              :key="worker.id"
              :class="[
                'rounded-lg border px-3 py-2.5 text-left text-sm transition-colors',
                incomingWorker?.id === worker.id
                  ? 'border-primary bg-primary/10 text-foreground'
                  : 'border-border bg-surface hover:border-primary/50 text-foreground',
              ]"
              @click="incomingWorker = worker"
            >
              <span class="block font-medium">{{ worker.full_name || worker.username }}</span>
              <span class="text-xs text-muted-foreground">{{ worker.role }}</span>
            </button>
          </div>

          <div v-if="incomingWorker">
            <label class="block text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">PIN Petugas Pengganti</label>
            <input
              ref="incomingPinInput"
              v-model="incomingPin"
              type="password"
              inputmode="numeric"
              maxlength="4"
              placeholder="••••"
              class="w-full rounded-lg border border-border bg-surface px-4 py-3 text-center text-2xl tracking-[0.5em] text-foreground placeholder:text-muted-foreground/40 focus:border-primary focus:outline-none"
              @keydown.enter="submitIncoming"
            />
          </div>

          <div v-if="errorMsg" class="rounded-lg bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
            {{ errorMsg }}
          </div>

          <div class="flex gap-2">
            <button
              class="rounded-lg border border-destructive/30 px-3 py-2.5 text-xs font-medium text-destructive hover:bg-destructive/10 transition-colors"
              @click="showForceLeave = true"
            >
              Terpaksa Pergi
            </button>
            <button
              :disabled="!incomingWorker || incomingPin.length < 4 || isLoading"
              class="flex-1 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground transition-opacity disabled:opacity-40"
              @click="submitIncoming"
            >
              <span v-if="isLoading">Memproses...</span>
              <span v-else>Konfirmasi Serah Terima</span>
            </button>
          </div>
        </div>
      </template>

      <!-- FORCE LEAVE confirmation -->
      <template v-else-if="internalStep === 'force'">
        <div class="mb-6 text-center">
          <div class="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
            <svg class="h-6 w-6 text-destructive" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <h2 class="text-lg font-semibold text-foreground">Terpaksa Meninggalkan Pos</h2>
          <p class="mt-1 text-sm text-muted-foreground">
            Admin akan diberitahu. Pos akan dianggap tidak terjaga sampai petugas baru check-in.
          </p>
        </div>

        <div class="space-y-3">
          <div>
            <label class="block text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">Alasan (wajib)</label>
            <input
              v-model="forceLeaveReason"
              type="text"
              maxlength="255"
              placeholder="Contoh: darurat keluarga, sakit mendadak..."
              class="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
            />
          </div>
          <div>
            <label class="block text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">Konfirmasi PIN Anda</label>
            <input
              v-model="forcePin"
              type="password"
              inputmode="numeric"
              maxlength="4"
              placeholder="••••"
              class="w-full rounded-lg border border-border bg-surface px-4 py-3 text-center text-2xl tracking-[0.5em] text-foreground placeholder:text-muted-foreground/40 focus:border-primary focus:outline-none"
              @keydown.enter="submitForceLeave"
            />
          </div>

          <div v-if="errorMsg" class="rounded-lg bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
            {{ errorMsg }}
          </div>

          <div class="flex gap-2">
            <button
              class="flex-1 rounded-lg border border-border px-4 py-3 text-sm font-medium text-foreground hover:bg-surface transition-colors"
              @click="internalStep = 'pending'; showForceLeave = false"
            >
              Kembali
            </button>
            <button
              :disabled="forcePin.length < 4 || !forceLeaveReason.trim() || isLoading"
              class="flex-1 rounded-lg bg-destructive px-4 py-3 text-sm font-semibold text-destructive-foreground transition-opacity disabled:opacity-40"
              @click="submitForceLeave"
            >
              <span v-if="isLoading">Memproses...</span>
              <span v-else>Tinggalkan Pos</span>
            </button>
          </div>
        </div>
      </template>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  sessionId: { type: Number, required: true },
  currentWorker: { type: Object, default: null },
  workers: { type: Array, default: () => [] },
  isLoading: { type: Boolean, default: false },
  // 'outgoing' = show outgoing confirm, 'pending' = already PENDING_HANDOVER
  initialStep: { type: String, default: 'outgoing' },
  earlyLeave: { type: Boolean, default: false },
})

const emit = defineEmits(['confirm-outgoing', 'confirm-incoming', 'force-leave', 'cancel'])

const internalStep = ref(props.initialStep)
const showForceLeave = ref(false)

const outgoingPin = ref('')
const endReason = ref('')
const incomingWorker = ref(null)
const incomingPin = ref('')
const forceLeaveReason = ref('')
const forcePin = ref('')
const errorMsg = ref('')

const outgoingPinInput = ref(null)
const incomingPinInput = ref(null)

const availableWorkers = computed(() =>
  props.workers.filter(w => w.id !== props.currentWorker?.id)
)

watch(showForceLeave, (val) => {
  if (val) internalStep.value = 'force'
})

watch(() => props.initialStep, (val) => {
  internalStep.value = val
})

watch(internalStep, async (val) => {
  errorMsg.value = ''
  if (val === 'outgoing') {
    outgoingPin.value = ''
    await nextTick()
    outgoingPinInput.value?.focus()
  }
})

watch(incomingWorker, async () => {
  incomingPin.value = ''
  await nextTick()
  incomingPinInput.value?.focus()
})

function initials(worker) {
  if (!worker) return '?'
  const name = worker.full_name || worker.username || '?'
  return name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
}

async function submitOutgoing() {
  if (outgoingPin.value.length < 4 || props.isLoading) return
  errorMsg.value = ''
  try {
    await emit('confirm-outgoing', {
      sessionId: props.sessionId,
      pin: outgoingPin.value,
      endType: props.earlyLeave ? 'EARLY' : 'SCHEDULED',
      endReason: endReason.value || null,
    })
    internalStep.value = 'pending'
  } catch (err) {
    errorMsg.value = err.message || 'PIN salah atau terjadi kesalahan'
    outgoingPin.value = ''
  }
}

async function submitIncoming() {
  if (!incomingWorker.value || incomingPin.value.length < 4 || props.isLoading) return
  errorMsg.value = ''
  try {
    await emit('confirm-incoming', {
      sessionId: props.sessionId,
      workerId: incomingWorker.value.id,
      pin: incomingPin.value,
    })
  } catch (err) {
    errorMsg.value = err.message || 'PIN salah atau terjadi kesalahan'
    incomingPin.value = ''
  }
}

async function submitForceLeave() {
  if (forcePin.value.length < 4 || !forceLeaveReason.value.trim() || props.isLoading) return
  errorMsg.value = ''
  try {
    await emit('force-leave', {
      sessionId: props.sessionId,
      pin: forcePin.value,
      reason: forceLeaveReason.value.trim(),
    })
  } catch (err) {
    errorMsg.value = err.message || 'PIN salah atau terjadi kesalahan'
    forcePin.value = ''
  }
}
</script>
