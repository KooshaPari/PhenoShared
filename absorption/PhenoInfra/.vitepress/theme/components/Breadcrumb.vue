<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vitepress'

export interface BreadcrumbItem {
  text: string
  link?: string
}

const props = defineProps<{
  items?: BreadcrumbItem[]
  separator?: string
}>()

const route = useRoute()

const breadcrumbs = computed(() => {
  if (props.items && props.items.length > 0) {
    return props.items
  }

  // Auto-generate from route
  const path = route.path
  const parts = path.split('/').filter(Boolean)

  const items: BreadcrumbItem[] = [
    { text: 'Home', link: '/' }
  ]

  let currentPath = ''
  parts.forEach((part, index) => {
    currentPath += `/${part}`
    const isLast = index === parts.length - 1
    items.push({
      text: part
        .split('-')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' '),
      link: isLast ? undefined : currentPath
    })
  })

  return items
})

const separator = computed(() => props.separator || '/')
</script>

<template>
  <nav class="breadcrumb" aria-label="Breadcrumb">
    <ol class="breadcrumb-list">
      <li
        v-for="(item, index) in breadcrumbs"
        :key="index"
        class="breadcrumb-item"
      >
        <component
          :is="item.link ? 'a' : 'span'"
          :href="item.link"
          :class="['breadcrumb-link', { 'breadcrumb-current': !item.link }]"
          :aria-current="!item.link ? 'page' : undefined"
        >
          {{ item.text }}
        </component>
        <span
          v-if="index < breadcrumbs.length - 1"
          class="breadcrumb-separator"
          aria-hidden="true"
        >
          {{ separator }}
        </span>
      </li>
    </ol>
  </nav>
</template>

<style scoped>
.breadcrumb {
  margin: var(--vp-spacing-4) 0;
}

.breadcrumb-list {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--vp-spacing-2);
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: var(--vp-font-size-sm);
  color: var(--vp-c-text-2);
}

.breadcrumb-item {
  display: flex;
  align-items: center;
  gap: var(--vp-spacing-2);
}

.breadcrumb-link {
  color: var(--vp-c-text-2);
  text-decoration: none;
  transition: color var(--vp-transition-fast) var(--vp-ease-out);
  border-radius: var(--vp-radius-sm);
  padding: var(--vp-spacing-1) var(--vp-spacing-2);
}

.breadcrumb-link:hover {
  color: var(--vp-c-brand);
  background: var(--vp-c-bg-soft);
}

.breadcrumb-link:focus-visible {
  outline: 2px solid var(--vp-c-brand);
  outline-offset: 2px;
}

.breadcrumb-current {
  color: var(--vp-c-text-1);
  font-weight: var(--vp-font-weight-medium);
  cursor: default;
}

.breadcrumb-current:hover {
  color: var(--vp-c-text-1);
  background: transparent;
}

.breadcrumb-separator {
  color: var(--vp-c-text-3);
  user-select: none;
}

/* Mobile adjustments */
@media (max-width: 640px) {
  .breadcrumb-list {
    font-size: var(--vp-font-size-xs);
  }

  .breadcrumb-link {
    padding: var(--vp-spacing-1);
  }
}
</style>
