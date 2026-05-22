<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
  <!-- Global toast surface — registered by plugins/toast.client.js. -->
  <Toaster
    position="top-right"
    rich-colors
    close-button
  />
</template>

<script setup>
import { Toaster } from 'vue-sonner'

useHead({
  titleTemplate: (title) => (title ? `${title} — E-Parking v2` : 'E-Parking v2'),
})
</script>
