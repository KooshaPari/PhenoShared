<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vitepress'

interface Tab {
  id: string
  label: string
}

const props = defineProps<{
  tabs?: Tab[]
  storageKey?: string
}>()

const route = useRoute()

// Use provided tabs or extract from slot content
const tabs = ref<Tab[]>(props.tabs || [])
const activeTabId = ref<string>('0')

// Generate storage key based on route if not provided
const storageKey = computed(() =>
  props.storageKey || `content-tabs-${route.path}`
)

// Load persisted tab from localStorage
function loadPersistedTab() {
  if (typeof window === 'undefined') return

  try {
    const saved = localStorage.getItem(storageKey.value)
    if (saved && tabs.value.find(t => t.id === saved)) {
      activeTabId.value = saved
    }
  } catch (e) {
    // Ignore localStorage errors
  }
}

// Save active tab to localStorage
function persistTab(tabId: string) {
  if (typeof window === 'undefined') return

  try {
    localStorage.setItem(storageKey.value, tabId)
  } catch (e) {
    // Ignore localStorage errors
  }
}

// Extract tabs from default slot content if not provided
onMounted(() => {
  if (props.tabs && props.tabs.length > 0) {
    tabs.value = props.tabs
  } else {
    // Try to extract tabs from the slot content
    const tabElements = document.querySelectorAll('[data-tab-id]')
    tabElements.forEach((el, index) => {
      const id = el.getAttribute('data-tab-id') || String(index)
      const label = el.getAttribute('data-tab-label') || id
      if (!tabs.value.find(t => t.id === id)) {
        tabs.value.push({ id, label })
      }
    })
  }

  // Set first tab as active if none selected
  if (tabs.value.length > 0 && !tabs.value.find(t => t.id === activeTabId.value)) {
    activeTabId.value = tabs.value[0].id
  }

  // Load persisted tab after tabs are available
  loadPersistedTab()
})

const activeTab = computed(() => {
  return tabs.value.find(t => t.id === activeTabId.value) || tabs.value[0]
})

function setActiveTab(tabId: string) {
  activeTabId.value = tabId
  persistTab(tabId)

  // Focus management for accessibility
  const button = document.querySelector(`[data-tab-button="${tabId}"]`) as HTMLElement
  if (button) {
    button.focus()
  }
}

// Watch for route changes and reset if needed
watch(() => route.path, () => {
  loadPersistedTab()
})

function handleKeydown(event: KeyboardEvent, _tabId: string) {
  if (tabs.value.length <= 1) return

  const currentIndex = tabs.value.findIndex(t => t.id === activeTabId.value)

  if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
    event.preventDefault()
    const nextIndex = (currentIndex + 1) % tabs.value.length
    setActiveTab(tabs.value[nextIndex].id)
  } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
    event.preventDefault()
    const prevIndex = (currentIndex - 1 + tabs.value.length) % tabs.value.length
    setActiveTab(tabs.value[prevIndex].id)
  } else if (event.key === 'Home') {
    event.preventDefault()
    setActiveTab(tabs.value[0].id)
  } else if (event.key === 'End') {
    event.preventDefault()
    setActiveTab(tabs.value[tabs.value.length - 1].id)
  }
}
</script>

<template>
  <div class="content-tabs">
    <div
      class="tab-list"
      role="tablist"
      :aria-label="activeTab?.label || 'Content tabs'"
    >
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :data-tab-button="tab.id"
        class="tab-button"
        :class="{ active: activeTabId === tab.id }"
        role="tab"
        :aria-selected="activeTabId === tab.id"
        :aria-controls="`tabpanel-${tab.id}`"
        :id="`tab-${tab.id}`"
        :tabindex="activeTabId === tab.id ? 0 : -1"
        @click="setActiveTab(tab.id)"
        @keydown="(e) => handleKeydown(e, tab.id)"
      >
        <span class="tab-label">{{ tab.label }}</span>
        <span
          v-if="activeTabId === tab.id"
          class="tab-indicator"
          aria-hidden="true"
        ></span>
      </button>
    </div>
    <TransitionGroup name="tab-panel">
      <div
        v-for="tab in tabs"
        :key="`${tab.id}-${activeTabId === tab.id}`"
        v-show="activeTabId === tab.id"
        :id="`tabpanel-${tab.id}`"
        class="tab-panel"
        :class="{ active: activeTabId === tab.id }"
        role="tabpanel"
        :aria-labelledby="`tab-${tab.id}`"
        :hidden="activeTabId !== tab.id"
      >
        <slot :name="`tab-${tab.id}`">
          <slot />
        </slot>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.content-tabs {
  margin: var(--vp-spacing-6) 0;
  border-radius: var(--vp-radius-md);
  overflow: hidden;
  background: var(--vp-c-bg);
  border: 1px solid var(--vp-c-divider);
  box-shadow: var(--vp-shadow-sm);
  transition: box-shadow var(--vp-transition-base) var(--vp-ease-out);
}

.content-tabs:hover {
  box-shadow: var(--vp-shadow-md);
}

.tab-list {
  display: flex;
  gap: var(--vp-spacing-1);
  padding: var(--vp-spacing-1) var(--vp-spacing-1) 0;
  background: var(--vp-c-bg-soft);
  border-bottom: 1px solid var(--vp-c-divider);
  overflow-x: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--vp-c-divider) transparent;
}

.tab-list::-webkit-scrollbar {
  height: 4px;
}

.tab-list::-webkit-scrollbar-track {
  background: transparent;
}

.tab-list::-webkit-scrollbar-thumb {
  background: var(--vp-c-divider);
  border-radius: 2px;
}

.tab-list::-webkit-scrollbar-thumb:hover {
  background: var(--vp-c-text-3);
}

.tab-button {
  position: relative;
  padding: var(--vp-spacing-3) var(--vp-spacing-5);
  border: none;
  background: transparent;
  color: var(--vp-c-text-2);
  font-size: var(--vp-font-size-sm);
  font-weight: var(--vp-font-weight-medium);
  cursor: pointer;
  border-radius: var(--vp-radius-md) var(--vp-radius-md) 0 0;
  transition: all var(--vp-transition-base) var(--vp-ease-out);
  white-space: nowrap;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tab-button:hover:not(.active) {
  color: var(--vp-c-text-1);
  background: var(--vp-c-bg);
}

.tab-button.active {
  color: var(--vp-c-brand);
  background: var(--vp-c-bg);
  font-weight: var(--vp-font-weight-semibold);
}

.tab-indicator {
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--vp-c-brand);
  border-radius: 2px 2px 0 0;
  animation: slide-in var(--vp-transition-base) var(--vp-ease-out);
}

@keyframes slide-in {
  from {
    transform: scaleX(0);
  }
  to {
    transform: scaleX(1);
  }
}

.tab-button:focus-visible {
  outline: 2px solid var(--vp-c-brand);
  outline-offset: -2px;
  z-index: 1;
}

.tab-label {
  position: relative;
  z-index: 1;
}

.tab-panel {
  padding: var(--vp-spacing-4);
  background: var(--vp-c-bg);
  min-height: 100px;
}

.tab-panel:has(> pre) {
  padding: 0;
}

.tab-panel:has(> pre) :deep(pre) {
  margin: 0;
  border-radius: 0 0 var(--vp-radius-md) var(--vp-radius-md);
}

/* Tab Panel Transitions */
.tab-panel-enter-active {
  transition: opacity var(--vp-transition-base) var(--vp-ease-out),
    transform var(--vp-transition-base) var(--vp-ease-out);
}

.tab-panel-leave-active {
  transition: opacity var(--vp-transition-fast) var(--vp-ease-in),
    transform var(--vp-transition-fast) var(--vp-ease-in);
}

.tab-panel-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.tab-panel-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* Mobile responsiveness */
@media (max-width: 640px) {
  .tab-button {
    padding: var(--vp-spacing-2) var(--vp-spacing-3);
    font-size: var(--vp-font-size-xs);
    min-height: 40px;
  }

  .tab-panel {
    padding: var(--vp-spacing-3);
  }
}
</style>
