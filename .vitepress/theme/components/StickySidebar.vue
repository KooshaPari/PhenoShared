<script setup lang="ts">
import { useData } from 'vitepress'

useData()
</script>

<template>
  <aside class="sticky-sidebar">
    <slot />
  </aside>
</template>

<style scoped>
.sticky-sidebar {
  position: sticky;
  top: var(--vp-header-height, 64px);
  max-height: calc(100vh - var(--vp-header-height, 64px));
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--vp-c-divider) transparent;
}

.sticky-sidebar::-webkit-scrollbar {
  width: 6px;
}

.sticky-sidebar::-webkit-scrollbar-track {
  background: transparent;
}

.sticky-sidebar::-webkit-scrollbar-thumb {
  background-color: var(--vp-c-divider);
  border-radius: 3px;
}

.sticky-sidebar::-webkit-scrollbar-thumb:hover {
  background-color: var(--vp-c-text-2);
}
</style>
