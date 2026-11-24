<script setup lang="ts">
// @trace FR-DOCS-009
import { ref, onMounted } from 'vue'

interface KBNode {
  title: string
  type: string
  status: string
  date: string
  path?: string
}

const nodes = ref<KBNode[]>([])

onMounted(async () => {
  try {
    const mod = await import('../../data/kb-graph.json')
    const data = mod.default ?? mod
    nodes.value = data.nodes ?? []
  } catch {
    nodes.value = []
  }
})
</script>

<template>
  <div class="kb-graph">
    <div v-if="nodes.length === 0" class="empty">No knowledge base entries yet.</div>
    <div v-for="node in nodes" :key="node.path ?? node.title" class="node">
      <span class="title">{{ node.title }}</span>
      <DocStatusBadge :status="node.status" />
    </div>
  </div>
</template>

<style scoped>
.kb-graph { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
.node { padding: 10px 12px; border: 1px solid var(--vp-c-divider); border-radius: 6px; display: flex; justify-content: space-between; align-items: center; }
.title { font-weight: 500; }
.empty { color: var(--vp-c-text-2); font-style: italic; }
</style>
