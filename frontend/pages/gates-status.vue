<template>
  <div>
    <PageHeader
      title="Monitoring Gerbang"
      subtitle="Status real-time. Gerbang masuk (daemon): hijau = online & controller responsif, kuning = controller bermasalah, merah = mati / tidak melapor > 60 detik. Gerbang keluar (booth): hijau = booth online, merah = booth tidak melapor > 60 detik."
    />

    <GateHeartbeatPanel />
  </div>
</template>

<script setup>
definePageMeta({
  middleware: ['auth'],
})
</script>
