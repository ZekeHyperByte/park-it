/**
 * useCrudPage composable
 *
 * Bundles the typical "list + create + edit + delete" boilerplate that every
 * admin tab needs. Use this in tab components instead of re-implementing
 * load/openCreate/openEdit/save/confirmDelete five times per page.
 *
 * Example:
 *   const page = useCrudPage('/api/members', {
 *     label: 'Member',
 *     columns: [...],
 *     fields: [...],
 *   })
 *
 *   page.load()                              // call in onMounted (or lazily on tab activate)
 *   page.openCreate()                        // open empty modal
 *   page.openEdit(row)                       // open populated modal
 *   page.save(formData)                      // create or update based on state
 *   page.confirmDelete(row)                  // open the confirm dialog
 *   page.executeDelete()                     // confirm dialog "Yes" handler
 *
 * @param {string} resourcePath
 * @param {object} options
 * @param {string} [options.label='Data']
 * @param {Array}  [options.columns=[]]
 * @param {Array}  [options.fields=[]]
 * @param {Function} [options.afterChange] — optional hook after create/update/delete
 */

import { ref } from 'vue'

export function useCrudPage(resourcePath, { label = 'Data', columns = [], fields = [], afterChange } = {}) {
  const crud = useCrud(resourcePath, { label })

  // List state
  const items = ref([])
  const loading = ref(false)
  const _loaded = ref(false)

  // Modal state
  const modalVisible = ref(false)
  const editing = ref(false)
  const form = ref({})
  const submitting = ref(false)

  // Delete dialog state
  const deleteDialog = ref({ visible: false, target: null, label: '' })

  async function load({ force = false } = {}) {
    if (loading.value) return
    if (_loaded.value && !force) return
    loading.value = true
    try {
      const result = await crud.list()
      // Support both shapes: {items,total,...} or bare arrays.
      items.value = Array.isArray(result) ? result : (result?.items ?? [])
      _loaded.value = true
    } finally {
      loading.value = false
    }
  }

  function openCreate() {
    editing.value = false
    form.value = {}
    modalVisible.value = true
  }

  function openEdit(row) {
    editing.value = true
    form.value = row ? { ...row } : {}
    modalVisible.value = true
  }

  async function save(data) {
    submitting.value = true
    try {
      if (editing.value && data.id != null) {
        await crud.update(data.id, data)
      } else {
        await crud.create(data)
      }
      modalVisible.value = false
      await load({ force: true })
      if (typeof afterChange === 'function') await afterChange('save')
    } finally {
      submitting.value = false
    }
  }

  function confirmDelete(row) {
    deleteDialog.value = {
      visible: true,
      target: row,
      label: row?.name || row?.code || row?.barcode || `#${row?.id ?? ''}`,
    }
  }

  async function executeDelete() {
    const target = deleteDialog.value.target
    if (!target) return
    submitting.value = true
    try {
      await crud.remove(target.id)
      deleteDialog.value.visible = false
      deleteDialog.value.target = null
      await load({ force: true })
      if (typeof afterChange === 'function') await afterChange('delete')
    } finally {
      submitting.value = false
    }
  }

  function cancelDelete() {
    deleteDialog.value.visible = false
    deleteDialog.value.target = null
  }

  return {
    // metadata (passed through for templates)
    label,
    columns,
    fields,

    // list
    items,
    loading,
    load,

    // modal
    modalVisible,
    editing,
    form,
    submitting,
    openCreate,
    openEdit,
    save,

    // delete
    deleteDialog,
    confirmDelete,
    executeDelete,
    cancelDelete,
  }
}
