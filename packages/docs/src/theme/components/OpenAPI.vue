<script setup lang="ts">
/**
 * OpenAPI - Embed OpenAPI/Swagger spec viewer.
 *
 * Usage in Markdown:
 * <OpenAPI spec-url="/api/openapi.json" />
 * <OpenAPI spec-url="https://api.example.com/openapi.json" />
 *
 * Uses Scalar's request proxy for CORS-friendly spec loading.
 */

import { computed } from 'vue'

const props = defineProps<{
  specUrl: string
}>()

const iframeSrc = computed(() => {
  if (!props.specUrl) return ''
  const encoded = encodeURIComponent(props.specUrl)
  return `https://api.scalar.com/request?url=${encoded}`
})
</script>

<template>
  <div v-if="specUrl" class="openapi-wrapper">
    <iframe
      :src="iframeSrc"
      title="OpenAPI Specification"
      class="openapi-iframe"
      loading="lazy"
    />
  </div>
</template>

<style scoped>
.openapi-wrapper {
  margin: 1rem 0;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--vp-c-divider);
}

.openapi-iframe {
  width: 100%;
  min-height: 500px;
  border: none;
}
</style>
