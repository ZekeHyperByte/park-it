<template>
  <Dialog :open="modelValue" @update:open="$emit('update:modelValue', $event)">
    <DialogContent class="max-w-sm">
      <DialogHeader>
        <DialogTitle>{{ title }}</DialogTitle>
      </DialogHeader>

      <p class="text-sm text-muted-foreground">{{ message }}</p>

      <DialogFooter>
        <Button variant="outline" @click="handleClose">Batal</Button>
        <Button variant="destructive" :disabled="loading" @click="handleConfirm">
          {{ loading ? 'Menghapus...' : 'Hapus' }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup>
import { Button } from '~/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '~/components/ui/dialog'

defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: 'Konfirmasi Hapus' },
  message: { type: String, default: 'Apakah Anda yakin ingin menghapus data ini?' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'confirm'])

function handleClose() {
  emit('update:modelValue', false)
}

function handleConfirm() {
  emit('confirm')
}
</script>
