<script setup lang="ts">
const props = defineProps<{ status: string }>()

const colorMap: Record<string, string> = {
  draft: '#888',
  active: '#2a9d8f',
  published: '#264653',
  archived: '#999',
  deprecated: '#e76f51',
  superseded: '#e9c46a',
}

const color = colorMap[props.status] ?? '#888'
</script>

<template>
  <span
    :style="{ backgroundColor: color, color: '#fff', padding: '2px 8px', borderRadius: '4px', fontSize: '0.8em', fontWeight: 600 }"
  >{{ status }}</span>
</template>
