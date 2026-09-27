<script setup lang="ts">
import { ref, provide } from 'vue'
import Toast from './Toast.vue'

export interface ToastItem {
  id: string
  message: string
  type?: 'success' | 'error' | 'warning' | 'info'
  duration?: number
  persistent?: boolean
}

const toasts = ref<ToastItem[]>([])

let toastIdCounter = 0

function showToast(message: string, options: Omit<ToastItem, 'id' | 'message'> = {}) {
  const id = `toast-${++toastIdCounter}`
  const toast: ToastItem = {
    id,
    message,
    type: options.type || 'info',
    duration: options.duration ?? 3000,
    persistent: options.persistent ?? false
  }

  toasts.value.push(toast)

  return id
}

function removeToast(id: string) {
  const index = toasts.value.findIndex(t => t.id === id)
  if (index > -1) {
    toasts.value.splice(index, 1)
  }
}

// Provide toast functions to child components
provide('toast', {
  show: showToast,
  success: (message: string, options?: Omit<ToastItem, 'id' | 'message' | 'type'>) =>
    showToast(message, { ...options, type: 'success' }),
  error: (message: string, options?: Omit<ToastItem, 'id' | 'message' | 'type'>) =>
    showToast(message, { ...options, type: 'error' }),
  warning: (message: string, options?: Omit<ToastItem, 'id' | 'message' | 'type'>) =>
    showToast(message, { ...options, type: 'warning' }),
  info: (message: string, options?: Omit<ToastItem, 'id' | 'message' | 'type'>) =>
    showToast(message, { ...options, type: 'info' })
})
</script>

<template>
  <Teleport to="body">
    <div class="toast-container" role="region" aria-label="Notifications">
      <Toast
        v-for="toast in toasts"
        :key="toast.id"
        :id="toast.id"
        :message="toast.message"
        :type="toast.type"
        :duration="toast.duration"
        :persistent="toast.persistent"
        @close="removeToast"
      />
    </div>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed;
  top: var(--vp-spacing-6);
  right: var(--vp-spacing-6);
  z-index: var(--vp-z-tooltip);
  display: flex;
  flex-direction: column;
  gap: var(--vp-spacing-2);
  pointer-events: none;
  max-width: calc(100vw - var(--vp-spacing-12));
}

.toast-container > * {
  pointer-events: auto;
}

/* Mobile adjustments */
@media (max-width: 640px) {
  .toast-container {
    top: var(--vp-spacing-4);
    right: var(--vp-spacing-4);
    left: var(--vp-spacing-4);
    max-width: none;
  }
}
</style>
