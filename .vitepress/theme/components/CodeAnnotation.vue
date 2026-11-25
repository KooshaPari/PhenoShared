<script setup lang="ts">
/**
 * CodeAnnotation - Line-by-line code annotations for VitePress.
 *
 * Usage in Markdown:
 * <CodeAnnotation :code="code" :annotations="annotations" />
 *
 * Or with slots:
 * <CodeAnnotation>
 *   <template #code><pre><code>...</code></pre></template>
 *   <template #annotation-1>Explanation for line 1</template>
 * </CodeAnnotation>
 */

import { computed } from 'vue'

export interface Annotation {
  line: number
  text: string
}

const props = withDefaults(
  defineProps<{
    code?: string
    language?: string
    annotations?: Annotation[]
    lineHeight?: number
  }>(),
  {
    lineHeight: 24,
  }
)

const lineHeightPx = computed(() => `${props.lineHeight}px`)
</script>

<template>
  <div class="code-annotation-wrapper">
    <div class="code-annotation">
      <pre class="code-block"><code>{{ code }}</code></pre>
      <div v-if="annotations?.length" class="annotations">
        <div
          v-for="(annotation, index) in annotations"
          :key="index"
          class="annotation"
          :style="{ top: `${(annotation.line - 1) * lineHeight}px` }"
        >
          <span class="annotation-line">{{ annotation.line }}</span>
          <span class="annotation-text">{{ annotation.text }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.code-annotation-wrapper {
  margin: 1rem 0;
}

.code-annotation {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--vp-c-divider);
}

.code-annotation .code-block {
  margin: 0;
  padding: 1rem 1rem 1rem 3rem;
  overflow-x: auto;
  font-size: 0.9em;
  line-height: v-bind(lineHeightPx);
  background: var(--vp-code-block-bg);
}

.code-annotation .code-block code {
  padding: 0;
  background: transparent;
}

.annotations {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.annotation {
  position: absolute;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0 1rem;
  min-height: v-bind(lineHeightPx);
  font-size: 0.85em;
  color: var(--vp-c-brand-1);
  background: rgba(var(--vp-c-brand-rgb), 0.08);
  border-left: 3px solid var(--vp-c-brand-1);
}

.annotation-line {
  flex-shrink: 0;
  font-weight: 600;
  opacity: 0.8;
}

.annotation-text {
  flex: 1;
}
</style>
