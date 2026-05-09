<template>
  <div>
    <DataTable
      :data="items"
      :columns="page.columns"
      :loading="loading"
      @add="page.openCreate()"
      @edit="page.openEdit"
      @delete="page.confirmDelete"
    />
    <CrudModal
      v-model="modalVisible"
      :title="editing ? `Edit ${page.label}` : `Tambah ${page.label}`"
      :fields="page.fields"
      :initial-data="form"
      :submitting="submitting"
      @submit="page.save"
    />
    <ConfirmDialog
      v-model="deleteDialogVisible"
      :title="`Hapus ${deleteLabel}`"
      :message="`Apakah Anda yakin ingin menghapus ${(deleteLabel || page.label).toLowerCase()}?`"
      :loading="submitting"
      @confirm="page.executeDelete"
      @cancel="page.cancelDelete"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'

/**
 * Renders a complete CRUD tab using a useCrudPage() instance.
 *
 * Usage:
 *   <CrudTab :page="memberPage" />
 */
const props = defineProps({
  page: { type: Object, required: true },
})

// Unwrap refs into computeds so the template stays tidy.
const items = computed(() => props.page.items.value)
const loading = computed(() => props.page.loading.value)
const editing = computed(() => props.page.editing.value)
const form = computed(() => props.page.form.value)
const submitting = computed(() => props.page.submitting.value)
const modalVisible = computed({
  get: () => props.page.modalVisible.value,
  set: (v) => (props.page.modalVisible.value = v),
})
const deleteDialogVisible = computed({
  get: () => props.page.deleteDialog.value.visible,
  set: (v) => {
    props.page.deleteDialog.value.visible = v
  },
})
const deleteLabel = computed(() => props.page.deleteDialog.value.label || '')
</script>
