<script setup lang="ts">
/**
 * AT2 — Custom skip link for VitePress.
 *
 * VitePress's default theme injects an English-only skip link. This component
 * overrides it with one that:
 *   1. Respects the active locale (en/es/ar) via the `t()`-style key
 *      passed as a prop, defaulting to "Skip to content".
 *   2. Targets VitePress's content wrapper, `id="VPContent"`, which is
 *      what the default theme renders around the page body.
 *   3. Uses the .a11y-skip-link class so keyboard focus reveals it
 *      (see a11y.css).
 *
 * WHY THE CLICK HANDLER EXISTS (WCAG 2.4.1, Bypass Blocks)
 *   `#VPContent` is a plain <div> with no `tabindex`, so it cannot take
 *   focus. Following the link scrolled the page but left the focus on the
 *   link itself, so the next Tab continued from the top of the document and
 *   the skip link skipped nothing - the exact failure WCAG 2.4.1 is about.
 *   The handler gives the target `tabindex="-1"` (the programmatic-focus
 *   convention, which does not add it to the tab order) and moves focus onto
 *   it. `href` is kept so the link still works when JavaScript has not run.
 */
defineProps<{ label?: string }>()

const TARGET_ID = 'VPContent'

function moveFocusToContent(): void {
  const target = document.getElementById(TARGET_ID)
  if (!target) {
    // No target on this page: leave the default fragment navigation alone.
    return
  }
  if (!target.hasAttribute('tabindex')) {
    target.setAttribute('tabindex', '-1')
  }
  target.focus()
}
</script>

<template>
  <a
    class="a11y-skip-link"
    href="#VPContent"
    @click="moveFocusToContent"
  >
    {{ label ?? 'Skip to content' }}
  </a>
</template>
