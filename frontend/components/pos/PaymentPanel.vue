<template>
  <div class="payment-panel">
    <!-- Idle State -->
    <div v-if="isIdle" class="idle-state">
      <div class="idle-icon">🚧</div>
      <h3>Palang Keluar</h3>
      <p class="idle-text">Menunggu kendaraan...</p>
      <div class="idle-shortcuts">
        <div class="shortcut-hint">F1: Cash</div>
        <div class="shortcut-hint">F2: RFID</div>
        <div class="shortcut-hint">F3: E-Money</div>
      </div>
    </div>

    <!-- Awaiting Gate Open State -->
    <div v-else-if="awaitingGateOpen" class="awaiting-state">
      <div class="success-icon">✅</div>
      <h3>Pembayaran Berhasil</h3>
      <p class="payment-summary">{{ formatCurrency(paidAmount) }} — Cash</p>
      <div class="receipt-status">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>Struk sedang dicetak...</span>
      </div>
      <div v-if="changeAmount > 0" class="change-amount">
        Kembalian: {{ formatCurrency(changeAmount) }}
      </div>
      <div class="divider"></div>
      <p class="open-instruction">Tekan SPACE atau klik untuk membuka palang</p>
      <el-button type="warning" size="large" class="open-gate-btn" @click="$emit('open-gate')">
        <el-icon><Unlock /></el-icon>
        BUKA PALANG
      </el-button>
    </div>

    <!-- E-Money Processing State -->
    <div v-else-if="emoneyActive" class="emoney-state">
      <div class="emoney-header">
        <span class="emoney-icon">💳</span>
        <h3>E-Money</h3>
      </div>
      <div class="emoney-card-info" v-if="emoneyCardInfo">
        <span>{{ emoneyCardInfo.cardType }}</span>
        <span class="card-number">{{ emoneyCardInfo.cardNumber }}</span>
      </div>
      <div class="emoney-status">
        <!-- WAITING_CARD -->
        <div v-if="emoneyState === 'WAITING_CARD'" class="emoney-message">
          <el-icon class="is-loading"><Loading /></el-icon>
          <p>Tempelkan kartu e-money</p>
        </div>
        <!-- PROCESSING -->
        <div v-else-if="emoneyState === 'PROCESSING'" class="emoney-message">
          <el-progress :percentage="50" :show-text="false" :stroke-width="8" class="emoney-progress" />
          <p>Memproses pembayaran...</p>
        </div>
        <!-- LOST_CONTACT -->
        <div v-else-if="emoneyState === 'LOST_CONTACT'" class="emoney-message emoney-warning">
          <p>Proses koreksi...</p>
          <p class="emoney-sub">Tempelkan kartu lagi</p>
        </div>
        <!-- WRONG_CARD -->
        <div v-else-if="emoneyState === 'WRONG_CARD'" class="emoney-message emoney-error">
          <p>Gunakan kartu sebelumnya</p>
        </div>
        <!-- INSUFFICIENT -->
        <div v-else-if="emoneyState === 'INSUFFICIENT'" class="emoney-message emoney-error">
          <p>Saldo tidak cukup</p>
          <p v-if="emoneyBalance" class="emoney-sub">Saldo: {{ formatCurrency(emoneyBalance) }}</p>
        </div>
        <!-- SUCCESS -->
        <div v-else-if="emoneyState === 'SUCCESS'" class="emoney-message emoney-success">
          <el-icon :size="32" color="var(--accent-green)"><CircleCheckFilled /></el-icon>
          <p>Pembayaran berhasil</p>
          <p v-if="emoneyBalance" class="emoney-sub">Saldo: {{ formatCurrency(emoneyBalance) }}</p>
        </div>
        <!-- FAILED -->
        <div v-else-if="emoneyState === 'FAILED'" class="emoney-message emoney-error">
          <p>Transaksi gagal</p>
        </div>
      </div>
      <div class="emoney-actions">
        <el-button
          v-if="['WRONG_CARD', 'INSUFFICIENT', 'FAILED'].includes(emoneyState)"
          type="success"
          @click="$emit('pay-cash')"
        >
          Bayar Cash
        </el-button>
        <el-button
          v-if="['WRONG_CARD', 'INSUFFICIENT', 'FAILED'].includes(emoneyState)"
          type="primary"
          @click="$emit('pay-rfid')"
        >
          Bayar RFID
        </el-button>
        <el-button
          v-if="['WAITING_CARD', 'PROCESSING', 'LOST_CONTACT'].includes(emoneyState)"
          @click="$emit('cancel-emoney')"
        >
          Batal
        </el-button>
        <el-button
          v-if="['WRONG_CARD', 'FAILED'].includes(emoneyState)"
          type="info"
          @click="$emit('retry-emoney')"
        >
          Coba Lagi
        </el-button>
      </div>
    </div>

    <!-- Active Payment State -->
    <div v-else class="payment-state">
      <div class="payment-header">
        <h3>Metode Pembayaran</h3>
        <span class="payment-total">{{ formatCurrency(tariff) }}</span>
      </div>
      <div class="divider"></div>

      <div class="payment-methods">
        <el-button class="payment-btn cash-btn" @click="$emit('pay-cash')">
          <div class="btn-content">
            <span class="btn-icon">💵</span>
            <span class="btn-label">CASH</span>
            <span class="btn-desc">Bayar tunai</span>
          </div>
        </el-button>

        <el-button class="payment-btn rfid-btn" @click="$emit('pay-rfid')">
          <div class="btn-content">
            <span class="btn-icon">🪪</span>
            <span class="btn-label">RFID</span>
            <span class="btn-desc">Kartu member</span>
          </div>
        </el-button>

        <el-button class="payment-btn emoney-btn" @click="$emit('pay-emoney')">
          <div class="btn-content">
            <span class="btn-icon">💳</span>
            <span class="btn-label">E-MONEY</span>
            <span class="btn-desc">Tap kartu e-money</span>
          </div>
        </el-button>
      </div>

      <!-- Barcode Scanner Input -->
      <div class="barcode-section">
        <el-input
          v-model="barcodeInput"
          placeholder="Scan barcode atau masukkan nopol"
          size="large"
          @keyup.enter="$emit('barcode-lookup', barcodeInput)"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
    </div>

    <!-- Cash Payment Modal -->
    <el-dialog
      v-model="cashModalVisible"
      title="Pembayaran Cash"
      width="520px"
      :close-on-click-modal="false"
      class="cash-dialog"
    >
      <div class="cash-modal">
        <div class="tariff-display">
          <span class="tariff-label">Tarif:</span>
          <span class="tariff-amount">{{ formatCurrency(tariff) }}</span>
        </div>

        <p class="denom-label">Uang Diterima:</p>
        <div class="denomination-grid">
          <el-button
            v-for="denom in denominations"
            :key="denom"
            class="denom-btn"
            :class="{ 'denom-exact': denom === tariff }"
            @click="selectDenomination(denom)"
          >
            {{ formatDenomination(denom) }}
          </el-button>
        </div>

        <p class="manual-label">Atau masukkan manual:</p>
        <el-input-number
          v-model="cashReceived"
          :min="0"
          :step="1000"
          size="large"
          controls-position="right"
          class="cash-input"
          @keyup.enter="confirmCash"
        />

        <div v-if="cashReceived > 0" class="change-display" :class="{ 'change-insufficient': cashReceived < tariff }">
          <span class="change-label">{{ cashReceived < tariff ? 'Kurang:' : 'Kembalian:' }}</span>
          <span class="change-amount">{{ formatCurrency(Math.abs(cashReceived - tariff)) }}</span>
        </div>

        <div class="cash-actions">
          <el-button @click="cashModalVisible = false">Batal (Esc)</el-button>
          <el-button
            type="success"
            :disabled="cashReceived < tariff"
            @click="confirmCash"
          >
            Konfirmasi (Enter)
          </el-button>
        </div>
      </div>
    </el-dialog>

    <!-- RFID Payment Modal -->
    <el-dialog
      v-model="rfidModalVisible"
      title="Pembayaran RFID"
      width="420px"
      :close-on-click-modal="false"
      class="rfid-dialog"
    >
      <div class="rfid-modal">
        <p class="rfid-label">Nomor Kartu RFID:</p>
        <el-input
          v-model="rfidCardNumber"
          placeholder="Masukkan atau tap kartu"
          size="large"
          @keyup.enter="confirmRfid"
        />
        <div class="rfid-actions">
          <el-button @click="rfidModalVisible = false">Batal</el-button>
          <el-button type="primary" :disabled="!rfidCardNumber" @click="confirmRfid">
            Konfirmasi
          </el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
const props = defineProps({
  paymentState: { type: String, default: 'IDLE' },
  emoneyState: { type: String, default: 'IDLE' },
  awaitingGateOpen: { type: Boolean, default: false },
  tariff: { type: Number, default: 0 },
  changeAmount: { type: Number, default: 0 },
  emoneyCardInfo: { type: Object, default: null },
  emoneyBalance: { type: Number, default: null },
})

const emit = defineEmits(['pay-cash', 'pay-rfid', 'pay-emoney', 'open-gate', 'cancel-emoney', 'retry-emoney', 'barcode-lookup', 'confirm-cash', 'confirm-rfid'])

const isIdle = computed(() => props.paymentState === 'IDLE')
const emoneyActive = computed(() => !['IDLE'].includes(props.emoneyState))

// Cash modal state
const cashModalVisible = ref(false)
const cashReceived = ref(0)

// RFID modal state
const rfidModalVisible = ref(false)
const rfidCardNumber = ref('')

// Barcode input
const barcodeInput = ref('')

// Quick denominations
const ALL_DENOMINATIONS = [10000, 15000, 20000, 50000, 100000, 200000]
const denominations = computed(() => {
  return ALL_DENOMINATIONS.filter(d => d >= props.tariff)
})

const paidAmount = computed(() => cashReceived.value)

function selectDenomination(amount) {
  cashReceived.value = amount
}

function confirmCash() {
  if (cashReceived.value >= props.tariff) {
    emit('confirm-cash', cashReceived.value)
    cashModalVisible.value = false
    cashReceived.value = 0
  }
}

function confirmRfid() {
  if (rfidCardNumber.value) {
    emit('confirm-rfid', rfidCardNumber.value)
    rfidModalVisible.value = false
    rfidCardNumber.value = ''
  }
}

function openCashModal() {
  cashReceived.value = props.tariff
  cashModalVisible.value = true
}

function openRfidModal() {
  rfidCardNumber.value = ''
  rfidModalVisible.value = true
}

function closeModals() {
  cashModalVisible.value = false
  rfidModalVisible.value = false
}

function formatCurrency(amount) {
  return `Rp ${new Intl.NumberFormat('id-ID').format(amount)}`
}

function formatDenomination(amount) {
  if (amount >= 1000) {
    return `Rp ${amount / 1000}K`
  }
  return `Rp ${amount}`
}

defineExpose({ openCashModal, openRfidModal, closeModals })
</script>

<style scoped>
.payment-panel {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* Idle State */
.idle-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  text-align: center;
}

.idle-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.idle-state h3 {
  color: var(--text-primary);
  font-size: 20px;
  margin: 0 0 8px;
}

.idle-text {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0 0 24px;
}

.idle-shortcuts {
  display: flex;
  gap: 16px;
}

.shortcut-hint {
  font-size: 12px;
  color: var(--text-muted);
  padding: 4px 8px;
  background: var(--bg-tertiary);
  border-radius: 4px;
}

/* Awaiting State */
.awaiting-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  text-align: center;
}

.success-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.awaiting-state h3 {
  color: var(--accent-green);
  font-size: 20px;
  margin: 0 0 8px;
}

.payment-summary {
  color: var(--text-primary);
  font-size: 16px;
  margin: 0 0 12px;
}

.receipt-status {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 14px;
  margin-bottom: 8px;
}

.change-amount {
  color: var(--accent-green);
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 12px;
}

.divider {
  height: 1px;
  background: var(--border-color);
  width: 100%;
  margin: 12px 0;
}

.open-instruction {
  color: var(--text-secondary);
  font-size: 13px;
  margin: 0 0 16px;
}

.open-gate-btn {
  width: 100%;
  height: 56px;
  font-size: 18px;
  font-weight: 700;
}

/* E-Money State */
.emoney-state {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.emoney-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.emoney-header h3 {
  color: var(--emoney-color);
  margin: 0;
}

.emoney-card-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border-radius: 6px;
  margin-bottom: 16px;
}

.card-number {
  font-family: 'Courier New', monospace;
  color: var(--text-secondary);
}

.emoney-status {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.emoney-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  text-align: center;
}

.emoney-message p {
  margin: 0;
  font-size: 16px;
  color: var(--text-primary);
}

.emoney-sub {
  font-size: 13px !important;
  color: var(--text-secondary) !important;
}

.emoney-warning p {
  color: var(--accent-orange) !important;
}

.emoney-error p {
  color: var(--accent-red) !important;
}

.emoney-success p {
  color: var(--accent-green) !important;
}

.emoney-progress {
  width: 200px;
}

.emoney-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 16px;
}

.emoney-actions .el-button {
  flex: 1;
}

/* Payment State */
.payment-state {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.payment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.payment-header h3 {
  color: var(--text-primary);
  margin: 0;
  font-size: 16px;
}

.payment-total {
  color: var(--accent-green);
  font-size: 18px;
  font-weight: 700;
}

.payment-methods {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.payment-btn {
  height: 72px;
  width: 100%;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  transition: all 0.15s ease;
}

.payment-btn:hover {
  border-color: var(--border-active);
  background: var(--bg-hover);
}

.btn-content {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.btn-icon {
  font-size: 20px;
}

.btn-label {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.btn-desc {
  font-size: 12px;
  color: var(--text-secondary);
}

.cash-btn:hover { border-color: var(--cash-color); }
.rfid-btn:hover { border-color: var(--rfid-color); }
.emoney-btn:hover { border-color: var(--emoney-color); }

.barcode-section {
  margin-top: auto;
  padding-top: 12px;
}

/* Cash Dialog */
.cash-dialog :deep(.el-dialog__body) {
  padding: 20px;
  background: var(--bg-secondary);
}

.cash-modal {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tariff-display {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: 8px;
}

.tariff-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.tariff-amount {
  font-size: 24px;
  font-weight: 700;
  color: var(--accent-green);
}

.denom-label, .manual-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
}

.denomination-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.denom-btn {
  height: 48px;
  font-size: 14px;
  font-weight: 600;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}

.denom-btn:hover {
  border-color: var(--cash-color);
}

.denom-exact {
  border-color: var(--cash-color);
  background: rgba(0, 214, 143, 0.1);
}

.cash-input {
  width: 100%;
}

.change-display {
  display: flex;
  justify-content: space-between;
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: 8px;
}

.change-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.change-amount {
  font-size: 18px;
  font-weight: 700;
  color: var(--accent-green);
}

.change-insufficient .change-amount {
  color: var(--accent-red);
}

.cash-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.cash-actions .el-button {
  flex: 1;
}

/* RFID Dialog */
.rfid-dialog :deep(.el-dialog__body) {
  padding: 20px;
  background: var(--bg-secondary);
}

.rfid-modal {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rfid-label {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

.rfid-actions {
  display: flex;
  gap: 12px;
}

.rfid-actions .el-button {
  flex: 1;
}
</style>
