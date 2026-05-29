<template>
  <div>
    <PageHeader title="Member" subtitle="Manajemen member RFID." />

    <CrudTab :page="memberPage" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import CrudTab from '~/components/admin/CrudTab.vue'

definePageMeta({ middleware: 'auth' })

const vehicleTypes = ref([])

const memberColumns = [
  { prop: 'name', label: 'Nama', sortable: true },
  { prop: 'card_number', label: 'No. Kartu', width: 150, sortable: true },
  { prop: 'plate_number', label: 'Plat', width: 120 },
  { prop: 'vehicle_type_name', label: 'Jenis', width: 120 },
  { prop: 'is_active', label: 'Aktif', type: 'boolean', width: 80 },
  { prop: 'valid_until', label: 'Berlaku Sampai', width: 140 },
]
const memberFields = computed(() => [
  { prop: 'name', label: 'Nama', type: 'text', required: true },
  { prop: 'card_number', label: 'Nomor Kartu', type: 'text', required: true },
  { prop: 'phone', label: 'Telepon', type: 'text' },
  { prop: 'email', label: 'Email', type: 'text' },
  { prop: 'address', label: 'Alamat', type: 'textarea' },
  { prop: 'plate_number', label: 'Nomor Plat', type: 'text' },
  {
    prop: 'vehicle_type_id',
    label: 'Jenis Kendaraan',
    type: 'select',
    options: vehicleTypes.value.map((vt) => ({ label: vt.name, value: vt.id })),
  },
  { prop: 'is_active', label: 'Aktif', type: 'boolean' },
  { prop: 'valid_from', label: 'Berlaku Dari', type: 'date' },
  { prop: 'valid_until', label: 'Berlaku Sampai', type: 'date' },
  { prop: 'notes', label: 'Catatan', type: 'textarea' },
])

const memberPage = useCrudPage('/api/members', {
  label: 'Member',
  columns: memberColumns,
  fields: memberFields.value,
})

watch(memberFields, (next) => {
  memberPage.fields.splice(0, memberPage.fields.length, ...next)
})

onMounted(async () => {
  await memberPage.load()
  const vtCrud = useCrud('/api/vehicle-types', { label: 'Jenis Kendaraan' })
  try {
    const result = await vtCrud.list()
    vehicleTypes.value = Array.isArray(result) ? result : (result?.items ?? [])
  } catch {
    /* error toasts emitted by useCrud */
  }
})
</script>
