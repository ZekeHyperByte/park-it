<template>
  <div class="flex h-screen flex-col overflow-hidden bg-background text-foreground">
    <!-- Status Bar -->
    <header class="flex h-20 shrink-0 items-center border-b border-border px-5 gap-3">
      <div class="flex-1 min-w-0">
        <slot name="status-bar" />
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 overflow-hidden">
      <slot />
    </main>

    <!-- Action Bar -->
    <footer class="flex h-20 shrink-0 items-center border-t border-border px-6">
      <slot name="action-bar" />
    </footer>
  </div>
</template>
