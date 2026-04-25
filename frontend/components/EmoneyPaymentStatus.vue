<template>
  <el-card class="emoney-status-card" :class="cardClass" shadow="never">
    <div class="flex items-center justify-between">
      <div class="status-text">
        <el-icon v-if="icon" :size="20" class="mr-2">
          <component :is="icon" />
        </el-icon>
        <span>{{ displayText }}</span>
      </div>

      <div class="status-actions">
        <el-button
          v-if="showCancel"
          size="small"
          @click="cancel"
        >
          Batal
        </el-button>
        <el-button
          v-if="showRetry"
          size="small"
          type="primary"
          @click="retry"
        >
          Coba Lagi
        </el-button>
        <el-button
          v-if="showOverride"
          size="small"
          type="danger"
          @click="override"
        >
          Override
        </el-button>
        <el-button
          v-if="showPayCash"
          size="small"
          type="warning"
          @click="payCash"
        >
          Bayar Tunai
        </el-button>
        <el-button
          v-if="showPayRfid"
          size="small"
          type="success"
          @click="payRfid"
        >
          Bayar RFID
        </el-button>
      </div>
    </div>

    <el-progress
      v-if="gateStore.emoneyPaymentState === 'PROCESSING' || gateStore.emoneyPaymentState === 'LOST_CONTACT'"
      :percentage="100"
      :indeterminate="true"
      :show-text="false"
      class="mt-2"
    />
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import {
  Loading,
  CircleCheck,
  CircleClose,
  Warning,
  CreditCard,
} from '@element-plus/icons-vue'

const gateStore = useGateStore()

const stateMap = {
  WAITING_CARD: { text: 'Tempelkan kartu e-money', icon: CreditCard, type: 'info' },
  PROCESSING: { text: 'Memproses pembayaran...', icon: Loading, type: 'primary' },
  LOST_CONTACT: { text: 'Proses koreksi...', icon: Loading, type: 'warning' },
  WRONG_CARD: { text: 'Gunakan kartu sebelumnya', icon: Warning, type: 'warning' },
  INSUFFICIENT: { text: 'Saldo tidak cukup', icon: Warning, type: 'warning' },
  SUCCESS: { text: 'Pembayaran berhasil', icon: CircleCheck, type: 'success' },
  FAILED: { text: 'Transaksi gagal', icon: CircleClose, type: 'danger' },
}

const current = computed(() => stateMap[gateStore.emoneyPaymentState] || stateMap.WAITING_CARD)

const displayText = computed(() => current.value.text)
const icon = computed(() => current.value.icon)
const cardClass = computed(() => `is-${current.value.type}`)

const showCancel = computed(() =>
  ['WAITING_CARD', 'WRONG_CARD', 'LOST_CONTACT'].includes(gateStore.emoneyPaymentState)
)
const showRetry = computed(() => gateStore.emoneyPaymentState === 'FAILED')
const showOverride = computed(() => gateStore.emoneyPaymentState === 'FAILED')
const showPayCash = computed(() => gateStore.emoneyPaymentState === 'INSUFFICIENT')
const showPayRfid = computed(() => gateStore.emoneyPaymentState === 'INSUFFICIENT')

function cancel() {
  gateStore.setEmoneyState('IDLE')
}

function retry() {
  gateStore.setEmoneyState('WAITING_CARD')
}

function override() {
  // Emit override event or call API
  ElMessage.warning('Override e-money — perlu konfirmasi supervisor')
}

function payCash() {
  gateStore.setEmoneyState('IDLE')
  // Trigger cash flow
}

function payRfid() {
  gateStore.setEmoneyState('IDLE')
  // Trigger RFID flow
}
</script>

<style scoped>
.emoney-status-card {
  border-left: 4px solid #dcdfe6;
}

.emoney-status-card.is-info {
  border-left-color: #909399;
}

.emoney-status-card.is-primary {
  border-left-color: #409eff;
}

.emoney-status-card.is-success {
  border-left-color: #67c23a;
}

.emoney-status-card.is-warning {
  border-left-color: #e6a23c;
}

.emoney-status-card.is-danger {
  border-left-color: #f56c6c;
}

.status-text {
  display: flex;
  align-items: center;
  font-weight: 500;
}

.status-actions {
  display: flex;
  gap: 8px;
}
</style>
