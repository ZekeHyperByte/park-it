<template>
  <div>
    <h1>Gate In Monitor</h1>
    <p>Halaman ini menampilkan status real-time dari setiap gate masuk.</p>

    <el-row :gutter="16" class="mt-3">
      <el-col
        v-for="gate in websiteStore.activeGateIns"
        :key="gate.id"
        :xs="24"
        :sm="12"
        :md="8"
        :lg="6"
        class="mb-3"
      >
        <el-card shadow="hover">
          <template #header>
            <div class="flex justify-between items-center">
              <strong>{{ gate.name }}</strong>
              <el-tag size="small" type="success">{{ gate.gate_mode }}</el-tag>
            </div>
          </template>
          <p>Area: {{ gate.area_parkir_id }}</p>
          <p>Protocol: {{ gate.protocol }}</p>
          <p>Status: <el-tag size="small" type="info">IDLE</el-tag></p>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
definePageMeta({
  middleware: 'auth',
})

const websiteStore = useWebsiteStore()

onMounted(() => {
  websiteStore.fetchGateIns()
})
</script>
