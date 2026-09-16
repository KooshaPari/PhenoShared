<script setup lang="ts">
import { computed } from 'vue'
import { useData } from 'vitepress'

interface Tab {
  text: string
  link: string
  icon?: string
}

const props = defineProps<{
  tabs: Tab[]
}>()

const { page } = useData()

const activeIndex = computed(() => {
  const currentPath = page.value.relativePath || ''
  return props.tabs.findIndex(tab => {
    if (tab.link === '/') {
      return currentPath === 'index.md' || currentPath === ''
    }
    return currentPath.startsWith(tab.link.replace(/^\//, '').replace(/\/$/, ''))
  })
})

function isActive(_tab: Tab, index: number): boolean {
  return activeIndex.value === index
}

function navigate(link: string): void {
  window.location.href = link
}
</script>

<template>
  <div class="nav-tabs">
    <nav class="tabs-nav" role="navigation" aria-label="Section navigation">
      <button
        v-for="(tab, index) in tabs"
        :key="index"
        class="tab-button"
        :class="{ active: isActive(tab, index) }"
        :aria-current="isActive(tab, index) ? 'page' : undefined"
        @click="navigate(tab.link)"
      >
        <span v-if="tab.icon" class="tab-icon">{{ tab.icon }}</span>
        <span class="tab-text">{{ tab.text }}</span>
      </button>
    </nav>
  </div>
</template>

<style scoped>
.nav-tabs {
  width: 100%;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--vp-c-divider);
}

.tabs-nav {
  display: flex;
  gap: 4px;
  overflow-x: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--vp-c-brand) transparent;
}

.tab-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: var(--vp-c-text-2);
  transition: all 0.2s ease;
  white-space: nowrap;
}

.tab-button:hover {
  color: var(--vp-c-text-1);
  background: var(--vp-c-bg-soft);
}

.tab-button.active {
  color: var(--vp-c-brand);
  border-bottom-color: var(--vp-c-brand);
}

.tab-icon {
  font-size: 16px;
}

.tab-text {
  font-family: var(--vp-font-family-base);
}

/* Responsive design */
@media (max-width: 640px) {
  .tab-button {
    padding: 10px 14px;
    font-size: 13px;
  }

  .tab-text {
    font-size: 13px;
  }
}

/* Hide scrollbar but allow scrolling */
.tabs-nav::-webkit-scrollbar {
  height: 4px;
}

.tabs-nav::-webkit-scrollbar-track {
  background: transparent;
}

.tabs-nav::-webkit-scrollbar-thumb {
  background: var(--vp-c-brand);
  border-radius: 2px;
}

.tabs-nav::-webkit-scrollbar-thumb:hover {
  background: var(--vp-c-brand-light);
}
</style>
