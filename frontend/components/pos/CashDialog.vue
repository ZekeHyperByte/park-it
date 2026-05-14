<template>
  <Dialog :open="open" @update:open="$emit('update:open', $event)">
    <DialogContent class="max-w-md">
      <DialogHeader>
        <DialogTitle>Pembayaran Tunai</DialogTitle>
      </DialogHeader>

      <div class="space-y-4">
        <!-- Tariff display -->
        <div class="text-center rounded-lg bg-surface p-4">
          <div class="text-xs text-muted-foreground uppercase tracking-wide">Total Tarif</div>
          <div class="text-3xl font-bold text-foreground tabular-nums">{{ formattedTariff }}</div>
        </div>

        <!-- Quick denomination buttons -->
        <div class="grid grid-cols-3 gap-2">
          <Button
            v-for="denom in filteredDenominations"
            :key="denom"
            variant="outline"
            class="h-12 font-mono tabular-nums"
            @click="paidAmount = denom"
          >
            {{ formatCurrency(denom) }}
          </Button>
        </div>

        <!-- Manual input -->
        <div class="space-y-2">
          <label class="text-sm text-muted-foreground">Jumlah Dibayar</label>
          <Input
            ref="amountInput"
            v-model.number="paidAmount"
            type="number"
            :min="tariff"
            class="h-12 text-lg font-mono tabular-nums"
            placeholder="0"
            @keydown.enter="onConfirm"
          />
        </div>

        <!-- Change calculation -->
        <div v-if="paidAmount >= tariff" class="rounded-lg bg-success/10 border border-success/20 p-3 text-center">
          <div class="text-xs text-muted-foreground uppercase tracking-wide">Kembalian</div>
          <div class="text-xl font-bold font-mono text-foreground tabular-nums">{{ formattedChange }}</div>
        </div>
      </div>

      <DialogFooter>
        <Button variant="outline" @click="$emit('update:open', false)">Batal</Button>
        <Button
          :disabled="paidAmount < tariff"
          class="bg-cash hover:bg-cash/90 text-white"
          @click="onConfirm"
        >
          Bayar
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useFormatters } from '~/composables/useFormatters'
import { Button } from '~/components/ui/button'
import { Input } from '~/components/ui/input'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '~/components/ui/dialog'

const props = defineProps({
  open: { type: Boolean, default: false },
  tariff: { type: Number, default: 0 },
})

const emit = defineEmits(['update:open', 'confirm'])

const { formatCurrency } = useFormatters()

const amountInput = ref(null)
const paidAmount = ref(0)

const denominations = [10000, 20000, 50000, 100000, 200000, 500000]

const filteredDenominations = computed(() =>
  denominations.filter((d) => d >= props.tariff)
)

const formattedTariff = computed(() => formatCurrency(props.tariff))
const formattedChange = computed(() => formatCurrency(paidAmount.value - props.tariff))

function onConfirm() {
  if (paidAmount.value >= props.tariff) {
    emit('confirm', paidAmount.value)
    emit('update:open', false)
    paidAmount.value = 0
  }
}

// Focus input when dialog opens; restore focus when closing
watch(() => props.open, (val) => {
  if (val) {
    paidAmount.value = props.tariff
    nextTick(() => amountInput.value?.$el?.querySelector('input')?.focus())
  } else {
    nextTick(() => {
      const barcodeInput = document.querySelector('[data-barcode-input]')
      barcodeInput?.focus()
    })
  }
})
</script>
