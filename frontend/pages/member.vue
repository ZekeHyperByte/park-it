<template>
  <div>
    <PageHeader title="Member" subtitle="Manajemen member RFID dan grup member." />

    <TabStrip v-model="activeTab" :tabs="tabs" />

    <CrudTab v-show="activeTab === 'members'" :page="memberPage" />
    <CrudTab v-show="activeTab === 'groups'" :page="groupPage" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import CrudTab from '~/components/admin/CrudTab.vue'

definePageMeta({ middleware: 'auth' })

const tabs = [
  { key: 'members', label: 'Member' },
  { key: 'groups', label: 'Grup Member' },
]

const activeTab = ref('members')

// Vehicle types and member groups feed the Member form's selects. We need
// these arrays in scope before declaring memberPage.fields, so they have to
// be plain refs we mutate after fetch (computed() inside fields ensures the
// modal sees fresh options after vehicleTypes loads).
const vehicleTypes = ref([])
const memberGroupOptions = ref([])

// Member CrudPage --------------------------------------------------------
const memberColumns = [
  { prop: 'name', label: 'Nama', sortable: true },
  { prop: 'card_number', label: 'No. Kartu', width: 150, sortable: true },
  { prop: 'plate_number', label: 'Plat', width: 120 },
  { prop: 'vehicle_type_name', label: 'Jenis', width: 120 },
  { prop: 'member_group_name', label: 'Grup', width: 120 },
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
  {
    prop: 'member_group_id',
    label: 'Grup Member',
    type: 'select',
    options: memberGroupOptions.value.map((g) => ({ label: g.name, value: g.id })),
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
// Keep page.fields in sync when vehicleTypes / groups load asynchronously.
watch(memberFields, (next) => {
  memberPage.fields.splice(0, memberPage.fields.length, ...next)
})

// Group CrudPage --------------------------------------------------------
const groupColumns = [
  { prop: 'name', label: 'Nama', sortable: true },
  { prop: 'code', label: 'Kode', width: 120, sortable: true },
  { prop: 'description', label: 'Keterangan' },
  { prop: 'is_active', label: 'Aktif', type: 'boolean', width: 80 },
]
const groupFields = [
  { prop: 'name', label: 'Nama', type: 'text', required: true },
  { prop: 'code', label: 'Kode', type: 'text', required: true },
  { prop: 'description', label: 'Keterangan', type: 'textarea' },
  { prop: 'is_active', label: 'Aktif', type: 'boolean' },
]
const groupPage = useCrudPage('/api/member-groups', {
  label: 'Grup Member',
  columns: groupColumns,
  fields: groupFields,
  // After mutating groups, refresh the dropdown options shown in member form.
  afterChange: () => loadGroupOptions(),
})

// Lazy-load tabs: only fetch the active tab's data. Switching tabs lazily
// loads on first activation, then caches.
watch(
  activeTab,
  async (tab) => {
    if (tab === 'members') await memberPage.load()
    if (tab === 'groups') await groupPage.load()
  },
  { immediate: true },
)

// Foreign-key dropdown sources -----------------------------------------
const vtCrud = useCrud('/api/vehicle-types', { label: 'Jenis Kendaraan' })
const gCrud = useCrud('/api/member-groups', { label: 'Grup Member' })

async function loadVehicleTypes() {
  try {
    const result = await vtCrud.list()
    vehicleTypes.value = Array.isArray(result) ? result : (result?.items ?? [])
  } catch {
    /* error toasts are emitted by useCrud when not silent */
  }
}
async function loadGroupOptions() {
  try {
    const result = await gCrud.list()
    memberGroupOptions.value = Array.isArray(result) ? result : (result?.items ?? [])
  } catch {
    /* ignored */
  }
}

onMounted(() => {
  loadVehicleTypes()
  loadGroupOptions()
})
</script>
