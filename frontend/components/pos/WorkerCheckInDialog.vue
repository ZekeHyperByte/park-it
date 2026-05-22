<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
    <div class="w-full max-w-md rounded-xl border border-border bg-background p-6 shadow-2xl">
      <!-- Header -->
      <div class="mb-6 text-center">
        <div class="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
          <svg class="h-6 w-6 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        </div>
        <h2 class="text-lg font-semibold text-foreground">Mulai Shift</h2>
        <p class="mt-1 text-sm text-muted-foreground">
          Pilih nama Anda dan masukkan PIN untuk memulai shift
        </p>
      </div>

      <!-- Step 1: Pick worker -->
      <div v-if="step === 'pick'" class="space-y-2">
        <p class="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-3">Pilih petugas</p>
        <button
          v-for="worker in workers"
          :key="worker.id"
          :class="[
            'w-full rounded-lg border px-4 py-3 text-left transition-colors',
            selectedWorker?.id === worker.id
              ? 'border-primary bg-primary/10 text-foreground'
              : 'border-border bg-surface hover:border-primary/50 hover:bg-surface/80 text-foreground',
          ]"
          @click="selectWorker(worker)"
        >
          <span class="font-medium">{{ worker.full_name || worker.username }}</span>
          <span class="ml-2 text-xs text-muted-foreground">{{ worker.role }}</span>
        </button>

        <div v-if="workers.length === 0" class="py-8 text-center text-sm text-muted-foreground">
          Tidak ada petugas tersedia — hubungi admin untuk mengatur PIN
        </div>

        <div class="mt-4 flex items-center gap-2">
          <label class="flex items-center gap-2 cursor-pointer select-none text-sm text-muted-foreground">
            <input v-model="isSubstitute" type="checkbox" class="accent-primary" />
            Saya menggantikan petugas lain
          </label>
        </div>

        <div v-if="isSubstitute" class="mt-2">
          <p class="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">Menggantikan siapa?</p>
          <select
            v-model="originalWorkerId"
            class="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
          >
            <option :value="null">— Pilih petugas asli —</option>
            <option v-for="w in workers.filter(w => w.id !== selectedWorker?.id)" :key="w.id" :value="w.id">
              {{ w.full_name || w.username }}
            </option>
          </select>
        </div>

        <button
          :disabled="!selectedWorker"
          class="mt-4 w-full rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground transition-opacity disabled:opacity-40"
          @click="step = 'pin'"
        >
          Lanjutkan
        </button>
      </div>

      <!-- Step 2: Enter PIN -->
      <div v-else-if="step === 'pin'" class="space-y-4">
        <div class="flex items-center gap-3 rounded-lg border border-border bg-surface px-4 py-3">
          <div class="flex h-8 w-8 items-center justify-center rounded-full bg-primary/20 text-primary font-bold text-sm">
            {{ initials(selectedWorker) }}
          </div>
          <span class="font-medium text-foreground">{{ selectedWorker?.full_name || selectedWorker?.username }}</span>
          <button class="ml-auto text-xs text-muted-foreground hover:text-foreground" @click="step = 'pick'">Ganti</button>
        </div>

        <div>
          <label class="block text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">Masukkan PIN (4 digit)</label>
          <input
            ref="pinInput"
            v-model="pin"
            type="password"
            inputmode="numeric"
            maxlength="4"
            placeholder="••••"
            class="w-full rounded-lg border border-border bg-surface px-4 py-3 text-center text-2xl tracking-[0.5em] text-foreground placeholder:text-muted-foreground/40 focus:border-primary focus:outline-none"
            @keydown.enter="submit"
          />
        </div>

        <div v-if="errorMsg" class="rounded-lg bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
          {{ errorMsg }}
        </div>

        <div class="flex gap-2">
          <button
            class="flex-1 rounded-lg border border-border px-4 py-3 text-sm font-medium text-foreground hover:bg-surface transition-colors"
            @click="step = 'pick'"
          >
            Kembali
          </button>
          <button
            :disabled="pin.length < 4 || isLoading"
            class="flex-1 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground transition-opacity disabled:opacity-40"
            @click="submit"
          >
            <span v-if="isLoading">Memproses...</span>
            <span v-else>Mulai Shift</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'

const props = defineProps({
  gateId: { type: Number, required: true },
  workers: { type: Array, default: () => [] },
  isLoading: { type: Boolean, default: false },
})

const emit = defineEmits(['check-in'])

const step = ref('pick')
const selectedWorker = ref(null)
const pin = ref('')
const errorMsg = ref('')
const isSubstitute = ref(false)
const originalWorkerId = ref(null)
const pinInput = ref(null)

function selectWorker(worker) {
  selectedWorker.value = worker
}

function initials(worker) {
  if (!worker) return '?'
  const name = worker.full_name || worker.username || '?'
  return name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
}

watch(step, async (val) => {
  if (val === 'pin') {
    pin.value = ''
    errorMsg.value = ''
    await nextTick()
    pinInput.value?.focus()
  }
})

async function submit() {
  if (pin.value.length < 4 || props.isLoading) return
  errorMsg.value = ''
  try {
    await emit('check-in', {
      gateId: props.gateId,
      workerId: selectedWorker.value.id,
      pin: pin.value,
      isSubstitute: isSubstitute.value,
      originalWorkerId: isSubstitute.value ? originalWorkerId.value : null,
    })
  } catch (err) {
    errorMsg.value = err.message || 'PIN salah atau terjadi kesalahan'
    pin.value = ''
  }
}
</script>
