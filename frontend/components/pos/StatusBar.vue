<template>
  <div class="status-bar">
    <!-- Left: Gate Identity -->
    <div class="status-left">
      <div class="gate-badge">
        <span class="gate-code">{{ gate?.code || '---' }}</span>
      </div>
      <span class="gate-name">{{ gate?.name || 'Memuat...' }}</span>
    </div>

    <!-- Center: Hardware Indicators -->
    <div class="status-center">
      <div
        v-for="indicator in indicators"
        :key="indicator.key"
        class="hardware-indicator"
        :title="indicator.tooltip"
      >
        <span class="status-dot" :style="{ color: indicator.color }">●</span>
        <span class="status-label">{{ indicator.label }}</span>
        <span v-if="indicator.subtext" class="status-subtext">{{ indicator.subtext }}</span>
      </div>
    </div>

    <!-- Right: Shift & Operator -->
    <div class="status-right">
      <div v-if="shiftInfo" class="shift-info">
        <span class="shift-name">{{ shiftInfo.name }}</span>
        <span class="shift-time">{{ shiftInfo.timeRange }}</span>
      </div>
      <div class="shift-counter">
        <span class="counter-icon">Rp</span>
        <span class="counter-amount">{{ formatCurrency(cashCollected) }}</span>
        <span class="counter-tx">({{ transactionCount }} tx)</span>
      </div>
      <div class="operator-info">
        <span class="operator-name">{{ user?.full_name || user?.username || '---' }}</span>
        <el-tag size="small" :type="user?.role === 'admin' ? 'danger' : 'success'">
          {{ user?.role || '---' }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  gate: { type: Object, default: null },
  hardwareStatus: { type: Object, default: null },
  user: { type: Object, default: null },
  cashCollected: { type: Number, default: 0 },
  transactionCount: { type: Number, default: 0 },
  shiftInfo: { type: Object, default: null },
})

const indicators = computed(() => {
  const hw = props.hardwareStatus || {}
  const getStatusColor = (status) => {
    switch (status) {
      case 'online': case 'ready': case 'active': case 'connected': return 'var(--accent-green)'
      case 'stale': case 'degraded': return 'var(--accent-orange)'
      case 'offline': case 'disconnected': case 'error': return 'var(--accent-red)'
      default: return 'var(--text-muted)'
    }
  }

  return [
    {
      key: 'controller',
      label: 'Controller',
      color: getStatusColor(hw.controller?.status),
      tooltip: `Controller: ${hw.controller?.status || 'unknown'}`,
    },
    {
      key: 'emoney',
      label: 'E-Money',
      color: getStatusColor(hw.emoney?.status),
      tooltip: `E-Money: ${hw.emoney?.status || 'unknown'}`,
    },
    {
      key: 'printer',
      label: 'Printer',
      color: getStatusColor(hw.printer?.status),
      subtext: hw.printer?.paperPercent != null ? `${hw.printer.paperPercent}%` : '',
      tooltip: `Printer: ${hw.printer?.paperPercent || 0}% paper remaining`,
    },
    {
      key: 'camera',
      label: 'Camera',
      color: getStatusColor(hw.camera?.status),
      tooltip: `Camera: ${hw.camera?.status || 'unknown'}`,
    },
    {
      key: 'websocket',
      label: 'WS',
      color: getStatusColor(hw.websocket?.status),
      tooltip: `WebSocket: ${hw.websocket?.status || 'unknown'}`,
    },
  ]
})

function formatCurrency(amount) {
  return new Intl.NumberFormat('id-ID').format(amount)
}
</script>

<style scoped>
.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  padding: 0 16px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.status-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 200px;
}

.gate-badge {
  background: var(--accent-blue);
  color: #fff;
  padding: 4px 12px;
  border-radius: 6px;
  font-weight: 700;
  font-size: 14px;
}

.gate-name {
  color: var(--text-secondary);
  font-size: 13px;
}

.status-center {
  display: flex;
  align-items: center;
  gap: 16px;
}

.hardware-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: default;
}

.status-dot {
  font-size: 10px;
  line-height: 1;
}

.status-label {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.status-subtext {
  font-size: 11px;
  color: var(--text-muted);
}

.status-right {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 280px;
  justify-content: flex-end;
}

.shift-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.shift-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.shift-time {
  font-size: 11px;
  color: var(--text-muted);
}

.shift-counter {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.counter-icon {
  font-size: 11px;
  color: var(--accent-green);
  font-weight: 700;
}

.counter-amount {
  font-size: 14px;
  font-weight: 700;
  color: var(--accent-green);
}

.counter-tx {
  font-size: 11px;
  color: var(--text-muted);
}

.operator-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.operator-name {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
}
</style>
