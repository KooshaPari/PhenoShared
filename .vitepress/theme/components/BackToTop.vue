<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const visible = ref(false)
const scrollThreshold = 400

function handleScroll() {
  visible.value = window.scrollY > scrollThreshold
}

function scrollToTop() {
  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  })
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll, { passive: true })
  handleScroll() // Check initial state
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<template>
  <Transition name="back-to-top">
    <button
      v-if="visible"
      class="back-to-top"
      @click="scrollToTop"
      aria-label="Back to top"
      title="Back to top"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="M18 15l-6-6-6 6" />
      </svg>
    </button>
  </Transition>
</template>

<style scoped>
.back-to-top {
  position: fixed;
  bottom: var(--vp-spacing-6);
  right: var(--vp-spacing-6);
  z-index: var(--vp-z-fixed);
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--vp-c-brand);
  color: white;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: var(--vp-shadow-lg);
  transition: all var(--vp-transition-base) var(--vp-ease-out);
  padding: 0;
}

.back-to-top:hover {
  background: var(--vp-c-brand-dark);
  transform: translateY(-2px);
  box-shadow: var(--vp-shadow-xl);
}

.back-to-top:active {
  transform: translateY(0);
}

.back-to-top:focus-visible {
  outline: 2px solid var(--vp-c-brand);
  outline-offset: 2px;
}

.back-to-top svg {
  width: 24px;
  height: 24px;
}

/* Animations */
.back-to-top-enter-active,
.back-to-top-leave-active {
  transition: all var(--vp-transition-base) var(--vp-ease-out);
}

.back-to-top-enter-from,
.back-to-top-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.8);
}

/* Mobile adjustments */
@media (max-width: 640px) {
  .back-to-top {
    bottom: var(--vp-spacing-4);
    right: var(--vp-spacing-4);
    width: 44px;
    height: 44px;
  }

  .back-to-top svg {
    width: 20px;
    height: 20px;
  }
}
</style>
