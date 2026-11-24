<script setup lang="ts">
/**
 * AT2 — Custom skip link for VitePress.
 *
 * VitePress's default theme injects an English-only skip link. This component
 * overrides it with one that:
 *   1. Respects the active locale (en/es/ar) via the `t()`-style key
 *      passed as a prop, defaulting to "Skip to content".
 *   2. Targets the page <main> element which VitePress renders with
 *      `id="main-content"` on the .VPDoc / .VPContent wrapper.
 *   3. Uses the .a11y-skip-link class so keyboard focus reveals it
 *      (see a11y.css).
 */
defineProps<{ label?: string }>()
</script>

<template>
  <a
    class="a11y-skip-link"
    href="#VPContent"
  >
    {{ label ?? 'Skip to content' }}
  </a>
</template>
