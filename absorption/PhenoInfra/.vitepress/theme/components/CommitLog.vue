<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface CommitEntry {
  sha: string
  date: string
  author: string
  subject: string
  repo?: string
}

const commits = ref<CommitEntry[]>([])

onMounted(async () => {
  try {
    const mod = await import('../../data/commit-log.json')
    commits.value = mod.default ?? mod
  } catch {
    commits.value = []
  }
})
</script>

<template>
  <div class="commit-log">
    <p v-if="commits.length === 0" class="empty">No commits loaded. Generate <code>commit-log.json</code> from <code>git log</code> in CI or locally.</p>
    <table v-else class="commit-table">
      <thead>
        <tr>
          <th>Date</th>
          <th>SHA</th>
          <th>Repo</th>
          <th>Author</th>
          <th>Subject</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in commits" :key="c.sha + c.date">
          <td class="date">{{ c.date }}</td>
          <td><code>{{ c.sha }}</code></td>
          <td>{{ c.repo ?? '—' }}</td>
          <td>{{ c.author }}</td>
          <td class="subject">{{ c.subject }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.commit-log { overflow-x: auto; margin: 1rem 0; }
.commit-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.commit-table th,
.commit-table td { padding: 8px 10px; border-bottom: 1px solid var(--vp-c-divider); text-align: left; }
.commit-table th { color: var(--vp-c-text-2); font-weight: 600; }
.date { white-space: nowrap; color: var(--vp-c-text-2); }
.subject { font-weight: 500; }
.empty { color: var(--vp-c-text-2); font-style: italic; }
</style>
