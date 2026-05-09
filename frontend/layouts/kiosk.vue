<template>
  <div class="flex h-screen flex-col overflow-hidden bg-background text-foreground">
    <!-- Status Bar -->
    <header class="flex h-12 shrink-0 items-center border-b border-border px-3 gap-2">
      <NuxtLink
        to="/"
        class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-surface hover:text-foreground"
        title="Kembali ke Dashboard"
      >
        <svg class="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
          <polyline points="9 22 9 12 15 12 15 22" />
        </svg>
      </NuxtLink>
      <div class="h-5 w-px bg-border shrink-0" />
      <div class="flex-1 min-w-0">
        <slot name="status-bar" />
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 overflow-hidden">
      <slot />
    </main>

    <!-- Action Bar -->
    <footer class="flex h-11 shrink-0 items-center border-t border-border px-4">
      <slot name="action-bar" />
    </footer>
  </div>
</template>
