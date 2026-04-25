<template>
  <el-dialog
    v-model="visible"
    :title="title"
    width="400px"
    align-center
    @close="handleClose"
  >
    <p class="confirm-message">{{ message }}</p>
    <template #footer>
      <el-button @click="handleClose">Batal</el-button>
      <el-button type="danger" :loading="loading" @click="handleConfirm">
        Hapus
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: 'Konfirmasi Hapus' },
  message: { type: String, default: 'Apakah Anda yakin ingin menghapus data ini?' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'confirm'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

function handleClose() {
  visible.value = false
}

function handleConfirm() {
  emit('confirm')
}
</script>

<style scoped>
.confirm-message {
  font-size: 14px;
  color: #606266;
  margin: 0;
}
</style>
