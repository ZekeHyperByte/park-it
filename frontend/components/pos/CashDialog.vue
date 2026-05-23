<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center sketch-backdrop p-6" @keydown.esc="close" tabindex="-1">
      <div class="sketch-box w-full max-w-3xl p-7">
        <!-- Header -->
        <div class="flex items-baseline justify-between mb-1">
          <div class="text-xs uppercase tracking-[0.2em] font-hand-tight text-sketch-muted">MODAL · BAYAR TUNAI</div>
          <div class="text-xs font-hand-tight text-sketch-muted">F1 dari layar utama</div>
        </div>
        <h2 class="font-hand text-4xl mb-5 leading-none">Bayar Tunai</h2>

        <!-- Three tiles: Tagihan / Diterima / Kembali -->
        <div class="grid grid-cols-3 gap-4 mb-6">
          <div class="sketch-tile p-4">
            <div class="text-[11px] uppercase tracking-widest font-hand-tight text-sketch-muted mb-1">TAGIHAN</div>
            <div class="font-hand text-3xl tabular-nums">{{ formatRp(tariff) }}</div>
          </div>
          <div class="sketch-tile is-active p-4">
            <div class="text-[11px] uppercase tracking-widest font-hand-tight text-sketch-muted mb-1">DITERIMA</div>
            <input
              ref="amountInput"
              v-model.number="paidAmount"
              type="number"
              :min="0"
              class="w-full bg-transparent outline-none font-hand text-3xl tabular-nums"
              placeholder="0"
              @keydown.enter.prevent="onConfirm"
              @keydown.esc.prevent="close"
            />
            <div class="text-[11px] font-hand-tight text-sketch-muted mt-1">ketik nominal · enter untuk lanjut</div>
          </div>
          <div class="sketch-tile p-4" :class="{ 'opacity-50': paidAmount < tariff }">
            <div class="text-[11px] uppercase tracking-widest font-hand-tight text-sketch-muted mb-1">KEMBALI</div>
            <div class="font-hand text-3xl tabular-nums">{{ formatRp(Math.max(0, paidAmount - tariff)) }}</div>
          </div>
        </div>

        <!-- Denomination shortcuts -->
        <div class="text-[11px] uppercase tracking-widest font-hand-tight text-sketch-muted mb-2">SHORTCUT NOMINAL</div>
        <div class="grid grid-cols-7 gap-2 mb-6">
          <button
            v-for="(denom, idx) in denominations"
            :key="denom"
            class="sketch-tile px-2 py-3 text-center"
            :class="{ 'is-active': paidAmount === denom }"
            @click="setDenom(denom)"
          >
            <div class="font-hand text-xl leading-none">{{ shortLabel(denom) }}</div>
            <div class="text-[10px] font-hand-tight text-sketch-muted">«{{ idx + 1 }}»</div>
          </button>
        </div>

        <!-- Footer hint + actions -->
        <div class="flex items-center justify-between">
          <div class="text-xs font-hand-body text-sketch-muted max-w-md">
            <div>Konfirmasi 1/7 — bisa juga ketik angka langsung.</div>
            <div class="mt-1 italic">setelah Enter, struk dicetak otomatis, layar pindah ke 'buka palang', tekan Space saat kembalian sudah diberikan.</div>
          </div>
          <div class="flex gap-2">
            <button class="sketch-btn" @click="close">
              <span class="sketch-chip mr-1 px-1.5 py-0">Esc</span> Batal
            </button>
            <button class="sketch-btn is-go" :disabled="paidAmount < tariff" @click="onConfirm">
              <span class="sketch-chip mr-1 px-1.5 py-0">Enter</span> DITERIMA →
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  tariff: { type: Number, default: 0 },
})
const emit = defineEmits(['update:open', 'confirm'])

const amountInput = ref(null)
const paidAmount = ref(0)

const denominations = [1000, 2000, 5000, 10000, 20000, 50000, 100000]

function formatRp(v) {
  return 'Rp ' + Number(v || 0).toLocaleString('id-ID')
}
function shortLabel(v) {
  if (v >= 1000) return (v / 1000) + 'rb'
  return String(v)
}
function setDenom(v) { paidAmount.value = v }
function close() { emit('update:open', false) }
function onConfirm() {
  if (paidAmount.value < props.tariff) return
  emit('confirm', paidAmount.value)
  emit('update:open', false)
}

// Numeric 1..7 → denominations
function onKey(e) {
  if (!props.open) return
  const idx = parseInt(e.key, 10)
  if (idx >= 1 && idx <= denominations.length) {
    paidAmount.value = denominations[idx - 1]
    e.preventDefault()
  }
}

watch(() => props.open, (val) => {
  if (val) {
    paidAmount.value = props.tariff
    nextTick(() => amountInput.value?.focus())
    window.addEventListener('keydown', onKey)
  } else {
    window.removeEventListener('keydown', onKey)
    nextTick(() => {
      const barcodeInput = document.querySelector('[data-barcode-input]')
      barcodeInput?.focus()
    })
  }
})
</script>
