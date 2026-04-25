<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>

<script setup>
// Root app component — layout and page routing handled here
useHead({
  titleTemplate: (title) => (title ? `${title} — E-Parking v2` : 'E-Parking v2'),
})
</script>
