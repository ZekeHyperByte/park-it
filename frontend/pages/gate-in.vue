<template>
  <div>
    <h1 class="text-xl font-semibold mb-4">Monitor Gate Masuk</h1>

    <el-row :gutter="16">
      <el-col
        v-for="gate in websiteStore.activeGateIns"
        :key="gate.id"
        :xs="24" :sm="12" :md="8" :lg="6"
        class="mb-4"
      >
        <el-card shadow="hover" :class="['gate-card', gateStatusClass(gate.code)]">
          <template #header>
            <div class="flex justify-between items-center">
              <strong>{{ gate.name }}</strong>
              <el-tag :type="gateStateTag(gate.code)" size="small">
                {{ gateStateLabel(gate.code) }}
              </el-tag>
            </div>
          </template>

          <div class="gate-info">
            <div class="mb-2">
              <el-tag :type="wsTagType(gate.code)" size="small" effect="plain">
                {{ wsConnected(gate.code) ? 'Online' : 'Offline' }}
              </el-tag>
              <el-tag type="info" size="small" effect="plain" class="ml-2">
                {{ gate.protocol?.toUpperCase() || 'N/A' }}
              </el-tag>
            </div>

            <div class="state-display mb-2">
              <strong>{{ stateLabel(gate.code) }}</strong>
            </div>

            <div class="stats text-sm" style="color: #909399;">
              <div>Kendaraan masuk: {{ vehicleCount(gate.code) }}</div>
              <div v-if="lastCard(gate.code)">Kartu: {{ lastCard(gate.code) }}</div>
              <div v-if="lastEvent(gate.code)">Event: {{ lastEvent(gate.code) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col v-if="websiteStore.activeGateIns.length === 0" :span="24">
        <el-empty description="Tidak ada gate masuk terdaftar" />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, reactive } from 'vue'

definePageMeta({ middleware: 'auth' })

const websiteStore = useWebsiteStore()
const { $ws } = useNuxtApp()

const gateStates = reactive({})
const vehicleCounts = reactive({})
const lastCards = reactive({})
const lastEvents = reactive({})

const stateLabels = {
  IDLE: 'Siap',
  VEHICLE_PRESENT: 'Kendaraan Datang',
  GATE_CLOSED: 'Gate Tertutup',
  WAITING_BUTTON: 'Menunggu Tiket',
  WAITING_CARD: 'Menunggu Kartu',
  VALIDATING: 'Memvalidasi',
  CHECKING_BALANCE: 'Cek Saldo',
  WAITING_PRINT_DECISION: 'Cetak Tiket?',
  PROCESSING: 'Memproses',
  OPENING: 'Gate Terbuka',
  ERROR: 'Error',
  TIMEOUT_ALERT: 'Timeout',
}

const stateTags = {
  IDLE: 'info',
  VEHICLE_PRESENT: 'primary',
  GATE_CLOSED: 'info',
  WAITING_BUTTON: 'warning',
  WAITING_CARD: 'warning',
  VALIDATING: 'warning',
  CHECKING_BALANCE: 'warning',
  WAITING_PRINT_DECISION: 'warning',
  PROCESSING: 'warning',
  OPENING: 'success',
  ERROR: 'danger',
  TIMEOUT_ALERT: 'danger',
}

let unsubscribers = []

function stateLabel(code) {
  return stateLabels[gateStates[code]?.state] || gateStates[code]?.state || '—'
}

function gateStateLabel(code) {
  const s = gateStates[code]?.state
  if (!s) return '—'
  return stateLabels[s] || s
}

function gateStateTag(code) {
  const s = gateStates[code]?.state
  return stateTags[s] || 'info'
}

function wsTagType(code) {
  return wsConnected(code) ? 'success' : 'danger'
}

function wsConnected(code) {
  return $ws.isConnected(code)
}

function vehicleCount(code) {
  return vehicleCounts[code] || 0
}

function lastCard(code) {
  return lastCards[code] || null
}

function lastEvent(code) {
  return lastEvents[code] || null
}

function gateStatusClass(code) {
  const s = gateStates[code]?.state
  if (s === 'OPENING') return 'gate-card-opening'
  if (s?.includes('WAITING') || s === 'VEHICLE_PRESENT' || s === 'PROCESSING') return 'gate-card-active'
  return ''
}

function handleEvent(code, event) {
  const type = event.event_type || event.type

  // Update state from heartbeat_state events
  if (type === 'heartbeat_state') {
    gateStates[code] = { state: event.state, ...event }
    return
  }

  // Update state from state machine events
  const stateMap = {
    'vehicle_detected': 'VEHICLE_PRESENT',
    'gate_closed': 'GATE_CLOSED',
    'rfid_card_read': 'VALIDATING',
    'passti_card_tap': 'CHECKING_BALANCE',
    'ticket_button_pressed': 'PROCESSING',
    'gate_opened': 'OPENING',
    'vehicle_passed': 'IDLE',
    'timeout_alert': 'TIMEOUT_ALERT',
    'vehicle_left': 'IDLE',
  }

  if (stateMap[type]) {
    gateStates[code] = { state: stateMap[type], ...event }
  }

  lastEvents[code] = type

  switch (type) {
    case 'vehicle_detected':
      vehicleCounts[code] = (vehicleCounts[code] || 0) + 1
      break
    case 'rfid_card_read':
    case 'passti_card_tap':
      lastCards[code] = event.card_number || event.card_type
      break
  }
}

onMounted(async () => {
  await websiteStore.loadAll()

  for (const gate of websiteStore.activeGateIns) {
    const code = gate.code
    gateStates[code] = { state: 'IDLE' }
    vehicleCounts[code] = 0

    const unsub = $ws.on(code, (event) => handleEvent(code, event))
    unsubscribers.push(unsub)
  }
})

onUnmounted(() => {
  unsubscribers.forEach(fn => fn())
  unsubscribers = []
})
</script>

<style scoped>
.gate-card {
  transition: border-left-color 0.3s ease;
}

.gate-card-opening {
  border-left: 4px solid #67c23a;
}

.gate-card-active {
  border-left: 4px solid #409eff;
}

.state-display {
  font-size: 16px;
  padding: 8px 0;
}

.stats {
  border-top: 1px solid #ebeef5;
  padding-top: 8px;
}

.ml-2 {
  margin-left: 8px;
}
</style>
