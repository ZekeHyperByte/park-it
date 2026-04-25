<template>
  <div>
    <h1>Member</h1>
    <p class="text-secondary mb-3">Manajemen member RFID dan grup member.</p>

    <el-tabs v-model="activeTab" type="border-card">
      <!-- Members -->
      <el-tab-pane label="Member" name="members">
        <DataTable
          :data="members"
          :columns="memberColumns"
          :loading="loadingMembers"
          @add="openMemberModal()"
          @edit="openMemberModal"
          @delete="confirmDeleteMember"
        />
      </el-tab-pane>

      <!-- Member Groups -->
      <el-tab-pane label="Grup Member" name="groups">
        <DataTable
          :data="memberGroups"
          :columns="groupColumns"
          :loading="loadingGroups"
          @add="openGroupModal()"
          @edit="openGroupModal"
          @delete="confirmDeleteGroup"
        />
      </el-tab-pane>
    </el-tabs>

    <!-- Member Modal -->
    <CrudModal
      v-model="memberModalVisible"
      :title="memberEditing ? 'Edit Member' : 'Tambah Member'"
      :fields="memberFields"
      :initial-data="memberForm"
      :submitting="submitting"
      @submit="saveMember"
    />

    <!-- Group Modal -->
    <CrudModal
      v-model="groupModalVisible"
      :title="groupEditing ? 'Edit Grup Member' : 'Tambah Grup Member'"
      :fields="groupFields"
      :initial-data="groupForm"
      :submitting="submitting"
      @submit="saveGroup"
    />

    <!-- Delete Confirm -->
    <ConfirmDialog
      v-model="deleteDialogVisible"
      :title="`Hapus ${deleteTargetName}`"
      :message="`Apakah Anda yakin ingin menghapus ${deleteTargetName}?`"
      :loading="submitting"
      @confirm="executeDelete"
    />
  </div>
</template>

<script setup>
definePageMeta({
  middleware: 'auth',
})

const { fetchApi } = useApi()
const memberCrud = useCrud('/api/members')
const groupCrud = useCrud('/api/member-groups')
const vehicleTypeCrud = useCrud('/api/vehicle-types')

const activeTab = ref('members')
const submitting = ref(false)

// Reference data for dropdowns
const vehicleTypes = ref([])
const memberGroups = ref([])

// Members
const members = ref([])
const loadingMembers = ref(false)
const memberModalVisible = ref(false)
const memberEditing = ref(false)
const memberForm = ref({})
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
    options: memberGroups.value.map((g) => ({ label: g.name, value: g.id })),
  },
  { prop: 'is_active', label: 'Aktif', type: 'boolean' },
  { prop: 'valid_from', label: 'Berlaku Dari', type: 'date' },
  { prop: 'valid_until', label: 'Berlaku Sampai', type: 'date' },
  { prop: 'notes', label: 'Catatan', type: 'textarea' },
])

// Member Groups
const loadingGroups = ref(false)
const groupModalVisible = ref(false)
const groupEditing = ref(false)
const groupForm = ref({})
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

// Delete dialog
const deleteDialogVisible = ref(false)
const deleteTargetName = ref('')
const deleteAction = ref(null)

// Load data
onMounted(() => {
  loadMembers()
  loadGroups()
  loadVehicleTypes()
})

async function loadVehicleTypes() {
  try {
    vehicleTypes.value = await vehicleTypeCrud.list()
  } catch (err) {
    ElMessage.error('Gagal memuat jenis kendaraan')
  }
}

// Members
async function loadMembers() {
  loadingMembers.value = true
  try {
    members.value = await memberCrud.list()
  } catch (err) {
    ElMessage.error('Gagal memuat member')
  } finally {
    loadingMembers.value = false
  }
}

function openMemberModal(row = null) {
  memberEditing.value = !!row
  memberForm.value = row ? { ...row } : {}
  memberModalVisible.value = true
}

async function saveMember(data) {
  submitting.value = true
  try {
    if (memberEditing.value) {
      await memberCrud.update(data.id, data)
    } else {
      await memberCrud.create(data)
    }
    memberModalVisible.value = false
    await loadMembers()
    ElMessage.success('Member disimpan')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menyimpan')
  } finally {
    submitting.value = false
  }
}

function confirmDeleteMember(row) {
  deleteTargetName.value = row.name
  deleteAction.value = () => deleteMember(row.id)
  deleteDialogVisible.value = true
}

async function deleteMember(id) {
  submitting.value = true
  try {
    await memberCrud.remove(id)
    deleteDialogVisible.value = false
    await loadMembers()
    ElMessage.success('Member dihapus')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menghapus')
  } finally {
    submitting.value = false
  }
}

// Groups
async function loadGroups() {
  loadingGroups.value = true
  try {
    memberGroups.value = await groupCrud.list()
  } catch (err) {
    ElMessage.error('Gagal memuat grup member')
  } finally {
    loadingGroups.value = false
  }
}

function openGroupModal(row = null) {
  groupEditing.value = !!row
  groupForm.value = row ? { ...row } : {}
  groupModalVisible.value = true
}

async function saveGroup(data) {
  submitting.value = true
  try {
    if (groupEditing.value) {
      await groupCrud.update(data.id, data)
    } else {
      await groupCrud.create(data)
    }
    groupModalVisible.value = false
    await loadGroups()
    ElMessage.success('Grup member disimpan')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menyimpan')
  } finally {
    submitting.value = false
  }
}

function confirmDeleteGroup(row) {
  deleteTargetName.value = row.name
  deleteAction.value = () => deleteGroup(row.id)
  deleteDialogVisible.value = true
}

async function deleteGroup(id) {
  submitting.value = true
  try {
    await groupCrud.remove(id)
    deleteDialogVisible.value = false
    await loadGroups()
    ElMessage.success('Grup member dihapus')
  } catch (err) {
    ElMessage.error(err.message || 'Gagal menghapus')
  } finally {
    submitting.value = false
  }
}

// Generic delete execution
function executeDelete() {
  if (deleteAction.value) deleteAction.value()
}
</script>
