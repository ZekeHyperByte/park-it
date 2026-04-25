<template>
  <div class="data-table-wrapper">
    <!-- Toolbar: search + add button -->
    <div class="table-toolbar mb-3">
      <el-input
        v-model="searchQuery"
        placeholder="Cari..."
        clearable
        style="width: 300px"
        @input="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button v-if="showAdd" type="primary" @click="$emit('add')">
        <el-icon><Plus /></el-icon> Tambah
      </el-button>
    </div>

    <!-- Table -->
    <el-table
      :data="displayedData"
      v-loading="loading"
      stripe
      style="width: 100%"
      @sort-change="handleSort"
    >
      <el-table-column
        v-for="col in columns"
        :key="col.prop"
        :prop="col.prop"
        :label="col.label"
        :width="col.width"
        :sortable="col.sortable ? 'custom' : false"
      >
        <template #default="{ row }">
          <template v-if="col.type === 'boolean'">
            <el-tag :type="row[col.prop] ? 'success' : 'info'" size="small">
              {{ row[col.prop] ? 'Ya' : 'Tidak' }}
            </el-tag>
          </template>
          <template v-else-if="col.type === 'enum'">
            <el-tag size="small">{{ row[col.prop] }}</el-tag>
          </template>
          <template v-else-if="col.formatter">
            {{ col.formatter(row[col.prop], row) }}
          </template>
          <template v-else>
            {{ row[col.prop] }}
          </template>
        </template>
      </el-table-column>

      <!-- Actions column -->
      <el-table-column v-if="showActions" label="Aksi" width="120" fixed="right">
        <template #default="{ row }">
          <el-button v-if="showEdit" type="primary" size="small" link @click="$emit('edit', row)">
            <el-icon><Edit /></el-icon>
          </el-button>
          <el-button v-if="showDelete" type="danger" size="small" link @click="$emit('delete', row)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Pagination -->
    <el-pagination
      v-if="showPagination && total > 0"
      class="mt-3"
      background
      layout="prev, pager, next, sizes, total"
      :total="total"
      :page-size="pageSize"
      :current-page="currentPage"
      :page-sizes="[10, 20, 50, 100]"
      @current-change="handlePageChange"
      @size-change="handleSizeChange"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Search, Plus, Edit, Delete } from '@element-plus/icons-vue'

const props = defineProps({
  data: { type: Array, default: () => [] },
  columns: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  showAdd: { type: Boolean, default: true },
  showEdit: { type: Boolean, default: true },
  showDelete: { type: Boolean, default: true },
  showActions: { type: Boolean, default: true },
  showPagination: { type: Boolean, default: true },
  pageSize: { type: Number, default: 10 },
})

const emit = defineEmits(['add', 'edit', 'delete', 'page-change', 'search'])

const searchQuery = ref('')
const currentPage = ref(1)
const currentPageSize = ref(props.pageSize)
const sortProp = ref('')
const sortOrder = ref('')

// Debounce search
let searchTimeout = null
function handleSearch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    emit('search', searchQuery.value)
  }, 300)
}

function handlePageChange(page) {
  currentPage.value = page
}

function handleSizeChange(size) {
  currentPageSize.value = size
  currentPage.value = 1
}

function handleSort({ prop, order }) {
  sortProp.value = prop || ''
  sortOrder.value = order || ''
}

// Filter + sort + paginate
const filteredData = computed(() => {
  let result = [...props.data]

  // Client-side search (if no server search)
  if (searchQuery.value && !props.loading) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter((row) =>
      props.columns.some((col) => {
        const val = String(row[col.prop] || '').toLowerCase()
        return val.includes(q)
      })
    )
  }

  // Sort
  if (sortProp.value && sortOrder.value) {
    const dir = sortOrder.value === 'ascending' ? 1 : -1
    result.sort((a, b) => {
      const av = a[sortProp.value]
      const bv = b[sortProp.value]
      if (av == null) return 1
      if (bv == null) return -1
      if (typeof av === 'number') return (av - bv) * dir
      return String(av).localeCompare(String(bv)) * dir
    })
  }

  return result
})

const total = computed(() => filteredData.value.length)

const displayedData = computed(() => {
  const start = (currentPage.value - 1) * currentPageSize.value
  return filteredData.value.slice(start, start + currentPageSize.value)
})
</script>

<style scoped>
.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.data-table-wrapper :deep(.el-table__header) {
  font-weight: 600;
}
</style>
