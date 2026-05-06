<template>
  <div class="photo-comparison">
    <div class="photo-panel" @click="openFullscreen">
      <div class="photo-label">
        <span class="label-text">MASUK</span>
        <span class="label-time">{{ entryTimeLabel }}</span>
      </div>
      <div class="photo-container">
        <img
          v-if="entryPhotoUrl"
          :src="entryPhotoUrl"
          alt="Foto Masuk"
          class="photo-image"
        />
        <div v-else class="photo-placeholder">
          <el-icon :size="48" color="var(--text-muted)"><Picture /></el-icon>
          <span class="placeholder-text">Foto masuk tidak tersedia</span>
        </div>
      </div>
      <div v-if="entryGateName" class="photo-gate">{{ entryGateName }}</div>
    </div>

    <div class="photo-panel" @click="openFullscreen">
      <div class="photo-label">
        <span class="label-text">KELUAR</span>
        <span class="label-time">{{ exitTimeLabel }}</span>
      </div>
      <div class="photo-container">
        <img
          v-if="exitPhotoUrl"
          :src="exitPhotoUrl"
          alt="Foto Keluar"
          class="photo-image"
        />
        <div v-else class="photo-placeholder">
          <el-icon :size="48" color="var(--text-muted)"><Camera /></el-icon>
          <span class="placeholder-text">Menunggu foto...</span>
        </div>
      </div>
      <div v-if="exitGateName" class="photo-gate">{{ exitGateName }}</div>
    </div>

    <!-- Fullscreen comparison modal -->
    <el-dialog
      v-model="fullscreenVisible"
      title="Perbandingan Foto"
      width="90%"
      :close-on-click-modal="true"
      class="fullscreen-dialog"
    >
      <div class="fullscreen-comparison">
        <div class="fullscreen-panel">
          <h4>Foto Masuk</h4>
          <img v-if="entryPhotoUrl" :src="entryPhotoUrl" alt="Foto Masuk" />
          <div v-else class="empty-state">Tidak tersedia</div>
        </div>
        <div class="fullscreen-panel">
          <h4>Foto Keluar</h4>
          <img v-if="exitPhotoUrl" :src="exitPhotoUrl" alt="Foto Keluar" />
          <div v-else class="empty-state">Tidak tersedia</div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
const props = defineProps({
  entryPhotoUrl: { type: String, default: null },
  exitPhotoUrl: { type: String, default: null },
  entryTime: { type: String, default: null },
  exitTime: { type: String, default: null },
  entryGateName: { type: String, default: null },
  exitGateName: { type: String, default: null },
})

const fullscreenVisible = ref(false)

const entryTimeLabel = computed(() => {
  if (!props.entryTime) return ''
  const d = new Date(props.entryTime)
  return d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })
})

const exitTimeLabel = computed(() => {
  if (!props.exitTime) return ''
  const d = new Date(props.exitTime)
  return d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })
})

function openFullscreen() {
  if (props.entryPhotoUrl || props.exitPhotoUrl) {
    fullscreenVisible.value = true
  }
}
</script>

<style scoped>
.photo-comparison {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 12px;
}

.photo-panel {
  position: relative;
  background: var(--bg-tertiary);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.15s ease;
}

.photo-panel:hover {
  transform: scale(1.01);
}

.photo-label {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 10px;
  background: linear-gradient(to bottom, rgba(0,0,0,0.7), transparent);
  z-index: 1;
}

.label-text {
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.5px;
}

.label-time {
  font-size: 11px;
  color: rgba(255,255,255,0.8);
}

.photo-container {
  aspect-ratio: 16 / 9;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-hover);
}

.photo-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.photo-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.placeholder-text {
  font-size: 12px;
  color: var(--text-muted);
}

.photo-gate {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 4px 10px;
  background: linear-gradient(to top, rgba(0,0,0,0.7), transparent);
  font-size: 11px;
  color: rgba(255,255,255,0.7);
  text-align: center;
}

.fullscreen-dialog :deep(.el-dialog__body) {
  padding: 16px;
  background: var(--bg-primary);
}

.fullscreen-comparison {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.fullscreen-panel {
  text-align: center;
}

.fullscreen-panel h4 {
  color: var(--text-primary);
  margin-bottom: 12px;
  font-size: 16px;
}

.fullscreen-panel img {
  width: 100%;
  max-height: 70vh;
  object-fit: contain;
  border-radius: 8px;
}

.empty-state {
  color: var(--text-muted);
  font-size: 18px;
  padding: 60px 0;
}
</style>
