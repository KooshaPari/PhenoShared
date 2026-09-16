<script setup lang="ts">
// @trace FR-DOCS-009
import { ref, onMounted } from 'vue'

interface AuditEntry {
  title: string
  date: string
  type: string
  status: string
  path?: string
}

const entries = ref<AuditEntry[]>([])

onMounted(async () => {
  try {
    const mod = await import('../../data/audit-log.json')
    entries.value = mod.default ?? mod
  } catch {
    entries.value = []
  }
})
</script>

<template>
  <div class="audit-timeline">
    <div v-if="entries.length === 0" class="empty">No audit entries yet.</div>
    <div v-for="entry in entries" :key="entry.path ?? entry.title" class="entry">
      <span class="date">{{ entry.date }}</span>
      <DocStatusBadge :status="entry.status" />
      <span class="title">{{ entry.title }}</span>
    </div>
  </div>
</template>

<style scoped>
.audit-timeline { display: flex; flex-direction: column; gap: 8px; }
.entry { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--vp-c-divider); }
.date { font-size: 0.8em; color: var(--vp-c-text-2); min-width: 90px; }
.title { flex: 1; }
.empty { color: var(--vp-c-text-2); font-style: italic; }
</style>
