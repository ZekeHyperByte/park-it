<template>
  <div class="flex items-center gap-2">
    <Button
      type="button"
      variant="outline"
      size="sm"
      :disabled="testing || !gateId"
      @click="runTest"
    >
      {{ testing ? 'Menguji…' : 'Test buka/tutup' }}
    </Button>
    <StatusPill v-if="status" :status="status" :label="label" />
    <span v-if="lastOpenMs" class="font-mono text-xs text-muted-foreground">
      buka: {{ lastOpenMs }}ms<span v-if="lastCloseMs">, tutup: {{ lastCloseMs }}ms</span>
    </span>
  </div>
  <p
    v-if="errorDetail"
    class="mt-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 font-mono text-xs text-destructive"
  >
    {{ errorDetail }}
  </p>
</template>

<script setup>
import { ref } from 'vue'
import { Button } from '~/components/ui/button'
import StatusPill from '~/components/setup/StatusPill.vue'

const props = defineProps({
  gateId: { type: Number, required: true },
  gateCode: { type: String, default: '' },
  timeoutS: { type: Number, default: 8.0 },
})

const { fetchApi } = useApi()

const testing = ref(false)
const status = ref('')
const label = ref('')
const errorDetail = ref('')
const lastOpenMs = ref(0)
const lastCloseMs = ref(0)

async function runTest() {
  testing.value = true
  status.value = 'testing'
  label.value = 'Mengirim perintah…'
  errorDetail.value = ''
  lastOpenMs.value = 0
  lastCloseMs.value = 0
  try {
    const res = await fetchApi('/api/setup/test-gate', {
      method: 'POST',
      body: JSON.stringify({ gate_id: props.gateId, timeout_s: props.timeoutS }),
    })
    const openStep = (res.steps || []).find((s) => s.action === 'open')
    const closeStep = (res.steps || []).find((s) => s.action === 'close')
    if (openStep?.elapsed_ms) lastOpenMs.value = Math.round(openStep.elapsed_ms)
    if (closeStep?.elapsed_ms) lastCloseMs.value = Math.round(closeStep.elapsed_ms)
    if (res.ok) {
      status.value = 'online'
      label.value = 'OK'
    } else {
      status.value = 'offline'
      label.value = 'Gagal'
      errorDetail.value = res.error || 'Tidak ada detail dari daemon.'
    }
  } catch (err) {
    status.value = 'offline'
    label.value = 'Gagal'
    errorDetail.value = err.message || String(err)
  } finally {
    testing.value = false
  }
}
</script>
