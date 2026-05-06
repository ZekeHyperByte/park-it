/**
 * Hardware Status Composable
 *
 * Polls printer status and aggregates hardware health indicators
 * for the POS status bar.
 */

export function useHardwareStatus() {
  const { fetchApi } = useApi()

  const hardwareStatus = ref({
    controller: { status: 'unknown', lastHeartbeat: null, label: 'Controller' },
    emoney: { status: 'unknown', enabled: false, label: 'E-Money' },
    printer: { status: 'unknown', paperPercent: 0, label: 'Printer' },
    camera: { status: 'unknown', enabled: false, label: 'Camera' },
    websocket: { status: 'unknown', label: 'WS' },
  })

  let pollInterval = null

  function getStatusColor(status) {
    switch (status) {
      case 'online':
      case 'ready':
      case 'active':
      case 'connected':
        return 'var(--accent-green)'
      case 'stale':
      case 'degraded':
        return 'var(--accent-orange)'
      case 'offline':
      case 'disconnected':
      case 'error':
        return 'var(--accent-red)'
      default:
        return 'var(--text-muted)'
    }
  }

  function getStatusIcon(status) {
    switch (status) {
      case 'online':
      case 'ready':
      case 'active':
      case 'connected':
        return '●'
      case 'stale':
      case 'degraded':
        return '●'
      case 'offline':
      case 'disconnected':
      case 'error':
        return '●'
      default:
        return '●'
    }
  }

  function updateFromGate(gate) {
    if (!gate) return

    const hw = gate.hardware_config || {}

    // Controller status from gate's is_online and last_heartbeat
    if (gate.is_online) {
      if (gate.last_heartbeat) {
        const lastHb = new Date(gate.last_heartbeat.replace(' ', 'T'))
        const age = (Date.now() - lastHb.getTime()) / 1000
        if (age < 60) {
          hardwareStatus.value.controller.status = 'online'
        } else if (age < 120) {
          hardwareStatus.value.controller.status = 'stale'
        } else {
          hardwareStatus.value.controller.status = 'offline'
        }
        hardwareStatus.value.controller.lastHeartbeat = gate.last_heartbeat
      } else {
        hardwareStatus.value.controller.status = 'online'
      }
    } else {
      hardwareStatus.value.controller.status = 'offline'
    }

    // E-Money reader
    const emoneyConfig = hw.emoney || {}
    hardwareStatus.value.emoney.enabled = emoneyConfig.enabled !== false
    hardwareStatus.value.emoney.status = emoneyConfig.enabled !== false ? 'ready' : 'offline'

    // Camera
    const cameraConfig = hw.camera || {}
    hardwareStatus.value.camera.enabled = cameraConfig.enabled !== false
    hardwareStatus.value.camera.status = cameraConfig.enabled !== false ? 'active' : 'disconnected'
  }

  function updateWebSocketStatus(connected) {
    hardwareStatus.value.websocket.status = connected ? 'connected' : 'disconnected'
  }

  async function refreshPrinterStatus() {
    try {
      const data = await fetchApi('/api/printers/status/summary')
      if (data && Array.isArray(data)) {
        // Find receipt printers (for booth)
        const receiptPrinters = data.filter(p => p.gate_type === 'OUT' || p.mode === 'SERIAL')
        if (receiptPrinters.length > 0) {
          const printer = receiptPrinters[0]
          const capacity = printer.paper_capacity || 300
          const remaining = printer.paper_remaining || 0
          const percent = Math.round((remaining / capacity) * 100)

          hardwareStatus.value.printer.paperPercent = percent
          if (percent > 50) {
            hardwareStatus.value.printer.status = 'online'
          } else if (percent > 10) {
            hardwareStatus.value.printer.status = 'stale'
          } else {
            hardwareStatus.value.printer.status = 'offline'
          }
        }
      }
    } catch (err) {
      console.warn('Failed to refresh printer status:', err)
    }
  }

  function startPolling(intervalMs = 60000) {
    refreshPrinterStatus()
    pollInterval = setInterval(refreshPrinterStatus, intervalMs)
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }

  return {
    hardwareStatus,
    getStatusColor,
    getStatusIcon,
    updateFromGate,
    updateWebSocketStatus,
    refreshPrinterStatus,
    startPolling,
    stopPolling,
  }
}
