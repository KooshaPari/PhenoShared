<script setup lang="ts">
withDefaults(defineProps<{
  size?: 'sm' | 'md' | 'lg'
  variant?: 'spinner' | 'dots' | 'pulse'
}>(), {
  size: 'md',
  variant: 'spinner'
})
</script>

<template>
  <div
    :class="['loading-spinner', `size-${size}`, `variant-${variant}`]"
    role="status"
    aria-label="Loading"
  >
    <span class="sr-only">Loading...</span>
    <div v-if="variant === 'spinner'" class="spinner-circle"></div>
    <div v-else-if="variant === 'dots'" class="spinner-dots">
      <span></span>
      <span></span>
      <span></span>
    </div>
    <div v-else-if="variant === 'pulse'" class="spinner-pulse"></div>
  </div>
</template>

<style scoped>
.loading-spinner {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

/* Size variants */
.size-sm {
  width: 16px;
  height: 16px;
}

.size-md {
  width: 24px;
  height: 24px;
}

.size-lg {
  width: 32px;
  height: 32px;
}

/* Spinner variant */
.spinner-circle {
  width: 100%;
  height: 100%;
  border: 2px solid var(--vp-c-divider);
  border-top-color: var(--vp-c-brand);
  border-radius: 50%;
  animation: spin var(--vp-transition-slower) linear infinite;
}

.size-sm .spinner-circle {
  border-width: 2px;
}

.size-md .spinner-circle {
  border-width: 3px;
}

.size-lg .spinner-circle {
  border-width: 4px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Dots variant */
.spinner-dots {
  display: flex;
  gap: 4px;
  align-items: center;
  justify-content: center;
}

.spinner-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--vp-c-brand);
  animation: dots-bounce 1.4s ease-in-out infinite both;
}

.size-sm .spinner-dots span {
  width: 4px;
  height: 4px;
}

.size-lg .spinner-dots span {
  width: 8px;
  height: 8px;
}

.spinner-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.spinner-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes dots-bounce {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* Pulse variant */
.spinner-pulse {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: var(--vp-c-brand);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(0.8);
  }
}

/* Dark mode adjustments */
.dark .spinner-circle {
  border-color: var(--vp-c-divider);
  border-top-color: var(--vp-c-brand);
}
</style>
