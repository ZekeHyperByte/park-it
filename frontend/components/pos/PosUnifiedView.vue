<template>
  <div class="flex h-full min-h-0 flex-col p-3 gap-2">
    <!-- Photos: fixed compact height, only when transaction active -->
    <div v-if="hasTransaction" class="flex-shrink-0 h-28">
      <PhotoComparison
        :entry-photo-url="entryPhotoUrl"
        :exit-photo-url="exitPhotoUrl"
        :entry-time="transaction?.entry_time"
        :entry-gate-name="transaction?.entry_gate_name"
      />
    </div>
    <div
      v-else
      class="flex-shrink-0 flex flex-col items-center justify-center py-4 gap-1 text-muted-foreground/30"
    >
      <ScanLine class="h-10 w-10" />
      <span class="text-sm">Scan barcode atau nomor plat kendaraan</span>
    </div>

    <!-- Transaction Info: flex-1 with overflow guard -->
    <div class="flex-1 min-h-0 overflow-y-auto space-y-2">
      <!-- Plate Number -->
      <div class="text-center">
        <div class="text-[10px] uppercase text-muted-foreground">Nomor Plat</div>
        <div
          :class="[
            'font-mono text-4xl font-black tracking-widest leading-tight',
            hasTransaction ? 'text-foreground' : 'text-muted-foreground/30'
          ]"
        >
          {{ transaction?.plate_number || '---' }}
        </div>
      </div>

      <!-- Info Row -->
      <div class="flex justify-center gap-4">
        <InfoItem label="Durasi" :value="formattedDuration" />
        <div class="h-8 w-px bg-border" />
        <InfoItem label="Masuk" :value="formattedEntryTime" />
        <div class="h-8 w-px bg-border" />
        <InfoItem label="Jenis" :value="vehicleTypeName" />
      </div>

      <!-- Price -->
      <div class="text-center py-1">
        <div class="text-xs uppercase text-muted-foreground">Total Parkir</div>
        <div
          :class="[
            'text-5xl font-black tabular-nums leading-tight',
            hasTransaction ? 'text-success' : 'text-muted-foreground/30'
          ]"
        >
          {{ formattedTariff }}
        </div>
      </div>

      <!-- E-money Status (only when relevant) -->
      <EmoneyInlineStatus
        v-if="showEmoneyStatus"
        :emoney-state="emoneyState"
        :card-info="cardInfo"
        :balance="balance"
        :has-card-number="!!transaction?.card_number"
        @retry="$emit('retry-emoney')"
        @cancel="$emit('cancel-emoney')"
      />

      <!-- Timeout Progress (only when relevant) -->
      <div v-if="showTimeout" class="space-y-1">
        <div class="flex items-center justify-between text-[10px]">
          <span class="uppercase tracking-wide text-muted-foreground">Waktu Tunggu</span>
          <span :class="timeoutTextColor" class="font-mono tabular-nums font-semibold">
            {{ waitingSeconds }}s / {{ timeoutSeconds }}s
          </span>
        </div>
        <div class="h-1 w-full rounded-full bg-surface/50 overflow-hidden">
          <div
            :class="['h-full rounded-full transition-all duration-1000', timeoutBarColor]"
            :style="{ width: `${timeoutPercent}%` }"
          />
        </div>
      </div>
    </div>

    <!-- Barcode Input: Always visible -->
    <div class="flex-shrink-0">
      <Input
        ref="barcodeInput"
        v-model="barcodeValue"
        data-barcode-input
        placeholder="Scan barcode atau masukkan nomor plat..."
        :disabled="awaitingGateOpen"
        class="h-12 text-center font-mono"
        @keydown.enter="onBarcodeSubmit"
      />
    </div>

    <!-- Payment Buttons: Always visible, disabled when no transaction -->
    <div class="flex-shrink-0 space-y-2">
      <PaymentButton
        icon="cash"
        label="TUNAI"
        shortcut="F1"
        :disabled="!canPayCash"
        :processing="isProcessing"
        @click="$emit('pay-cash')"
      />
      <PaymentButton
        icon="rfid"
        label="MEMBER RFID"
        shortcut="F2"
        :disabled="!canPayRfid"
        :processing="isProcessing"
        @click="$emit('pay-rfid')"
      />
      <PaymentButton
        icon="emoney"
        label="E-MONEY"
        shortcut="F3"
        :disabled="!canPayEmoney"
        :processing="isProcessing"
        @click="$emit('pay-emoney')"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { ScanLine } from 'lucide-vue-next'
import { useFormatters } from '~/composables/useFormatters'
import { Input } from '~/components/ui/input'
import PhotoComparison from './PhotoComparison.vue'
import InfoItem from './InfoItem.vue'
import PaymentButton from './PaymentButton.vue'
import EmoneyInlineStatus from './EmoneyInlineStatus.vue'

const props = defineProps({
  transaction: { type: Object, default: null },
  durationSeconds: { type: Number, default: 0 },
  waitingSeconds: { type: Number, default: 0 },
  paymentState: { type: String, default: 'IDLE' },
  emoneyState: { type: String, default: 'IDLE' },
  vehicleTypes: { type: Array, default: () => [] },
  entryPhotoUrl: { type: String, default: null },
  exitPhotoUrl: { type: String, default: null },
  timeoutSeconds: { type: Number, default: 120 },
  canPayCash: { type: Boolean, default: false },
  canPayRfid: { type: Boolean, default: false },
  canPayEmoney: { type: Boolean, default: false },
  cardInfo: { type: Object, default: null },
  balance: { type: Number, default: null },
  awaitingGateOpen: { type: Boolean, default: false },
  isProcessing: { type: Boolean, default: false },
})

const emit = defineEmits([
  'barcode-lookup',
  'pay-cash',
  'pay-rfid',
  'pay-emoney',
  'retry-emoney',
  'cancel-emoney',
])

const { formatCurrency, formatDuration, formatTime } = useFormatters()

const barcodeInput = ref(null)
const barcodeValue = ref('')

// Computed
const hasTransaction = computed(() => props.transaction !== null)

const formattedTariff = computed(() => {
  if (!hasTransaction.value) return 'Rp -----'
  return formatCurrency(props.transaction?.tariff || props.transaction?.fee || 0)
})

const formattedDuration = computed(() => {
  if (!hasTransaction.value) return null
  return formatDuration(props.durationSeconds)
})

const formattedEntryTime = computed(() => {
  if (!hasTransaction.value) return null
  return formatTime(props.transaction?.entry_time)
})

const vehicleTypeName = computed(() => {
  if (!hasTransaction.value || !props.transaction?.vehicle_type_id) return null
  const vt = props.vehicleTypes.find((t) => t.id === props.transaction.vehicle_type_id)
  return vt?.name || props.transaction.vehicle_type || null
})

const timeoutPercent = computed(() => {
  if (props.timeoutSeconds <= 0) return 0
  return Math.min(100, (props.waitingSeconds / props.timeoutSeconds) * 100)
})

const timeoutBarColor = computed(() => {
  if (timeoutPercent.value >= 90) return 'bg-destructive'
  if (timeoutPercent.value >= 70) return 'bg-warning'
  return 'bg-success'
})

const timeoutTextColor = computed(() => {
  if (timeoutPercent.value >= 90) return 'text-destructive'
  if (timeoutPercent.value >= 70) return 'text-warning'
  return 'text-success'
})

const showTimeout = computed(() => {
  return hasTransaction.value && (props.paymentState === 'WAITING_PAYMENT' || props.paymentState === 'TIMEOUT_ALERT')
})

const showEmoneyStatus = computed(() => {
  return hasTransaction.value && props.emoneyState !== 'IDLE'
})

// Methods
function onBarcodeSubmit() {
  if (barcodeValue.value.trim() && !props.awaitingGateOpen) {
    emit('barcode-lookup', barcodeValue.value.trim())
    barcodeValue.value = ''
  }
}

function focusBarcode() {
  nextTick(() => {
    const ref = barcodeInput.value
    const el = ref?.$el ?? ref
    const input = el?.querySelector?.('input') ?? (el?.tagName === 'INPUT' ? el : null)
    input?.focus?.()
  })
}

// Focus management: Always keep barcode input focused
watch(() => props.transaction, () => {
  // Don't steal focus when transaction arrives - let operator continue scanning
  nextTick(() => {
    if (!props.transaction) {
      focusBarcode()
    }
  })
})

watch(() => props.awaitingGateOpen, (isAwaiting) => {
  if (!isAwaiting) {
    focusBarcode()
  }
})

onMounted(() => {
  focusBarcode()
})

defineExpose({ focusBarcode })
</script>
