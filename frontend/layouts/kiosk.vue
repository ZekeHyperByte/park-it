<template>
  <div class="flex h-screen flex-col overflow-hidden bg-background text-foreground">
    <!-- Status Bar -->
    <header class="flex h-20 shrink-0 items-center border-b-4 border-foreground bg-foreground text-background px-5 gap-3">
      <div class="flex-1 min-w-0">
        <slot name="status-bar" />
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 overflow-hidden">
      <slot />
    </main>

    <!-- Action Bar -->
    <footer class="flex h-20 shrink-0 items-center border-t-4 border-foreground bg-primary px-6">
      <slot name="action-bar" />
    </footer>
  </div>
</template>
