<template>
  <div class="mx-auto max-w-6xl space-y-6 p-4">
    <header>
      <h1 class="text-xl font-bold text-foreground">Monitoring Gerbang</h1>
      <p class="text-sm text-muted-foreground">
        Status daemon real-time. Indikator hijau = daemon online &amp; controller responsif.
        Kuning = controller bermasalah. Merah = daemon mati / tidak melapor &gt; 60 detik.
      </p>
    </header>

    <GateHeartbeatPanel />
  </div>
</template>

<script setup>
definePageMeta({
  middleware: ['auth'],
})
</script>
