<script setup lang="ts">
/**
 * AT3 — Custom VitePress Layout.
 *
 * Extends the default layout to:
 *   1. Inject a singleton live region (`#doc-live`) for SPA route
 *      changes — VitePress re-renders content in-place, so AT users
 *      otherwise miss navigation context.
 *   2. Provide an `announce()` function via Vue provide/inject so any
 *      component in the theme tree can post status messages to the
 *      live region.
 *   3. Announce the page <h1> on every route change.
 */
import { provide, ref, watch, onMounted } from 'vue'
import { useRoute, useData } from 'vitepress'
import DefaultTheme from 'vitepress/theme'
import SkipLink from './SkipLink.vue'

const { Layout: DefaultLayout } = DefaultTheme
const route = useRoute()
const { title } = useData()

const liveMessage = ref('')
const liveNonce = ref(0)

provide('a11y:announce', (message: string) => {
  // Bump the nonce so SR re-reads even when the same text is repeated.
  liveNonce.value += 1
  liveMessage.value = message
})

function announcePageTitle() {
  liveMessage.value = ''
  liveNonce.value += 1
  // Defer so the live region "clears" before the new message lands.
  requestAnimationFrame(() => {
    liveMessage.value = `Navigated to: ${title.value}`
  })
}

onMounted(announcePageTitle)
watch(() => route.path, announcePageTitle)
</script>

<template>
  <div>
    <SkipLink />
    <!-- AT3: live region for SPA navigation announcements. -->
    <div
      id="doc-live"
      aria-live="polite"
      aria-atomic="true"
      role="status"
    >
      {{ liveMessage }}
    </div>
    <DefaultLayout />
  </div>
</template>
