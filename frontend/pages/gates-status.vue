<template>
  <div>
    <PageHeader
      title="Monitoring Gerbang"
      subtitle="Status daemon real-time. Indikator hijau = daemon online & controller responsif. Kuning = controller bermasalah. Merah = daemon mati / tidak melapor > 60 detik."
    />

    <GateHeartbeatPanel />
  </div>
</template>

<script setup>
definePageMeta({
  middleware: ['auth'],
})
</script>
