<template>
  <div>
    <h1>Member</h1>
    <p>Manajemen member dan grup.</p>
  </div>
</template>

<script setup>
definePageMeta({
  middleware: 'auth',
})
</script>
