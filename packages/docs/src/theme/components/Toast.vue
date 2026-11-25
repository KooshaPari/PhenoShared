<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

export interface ToastOptions {
  type?: 'success' | 'error' | 'warning' | 'info'
  duration?: number
  persistent?: boolean
}

const props = withDefaults(defineProps<{
  message: string
  type?: ToastOptions['type']
  duration?: number
  persistent?: boolean
  id?: string
}>(), {
  type: 'info',
  duration: 3000,
  persistent: false
})

const emit = defineEmits<{
  close: [id: string]
}>()

const visible = ref(false)
const timer = ref<number | null>(null)

onMounted(() => {
  // Trigger animation
  requestAnimationFrame(() => {
    visible.value = true
  })

  // Auto-dismiss if not persistent
  if (!props.persistent && props.duration > 0) {
    timer.value = window.setTimeout(() => {
      close()
    }, props.duration)
  }
})

onUnmounted(() => {
  if (timer.value) {
    clearTimeout(timer.value)
  }
})

function close() {
  visible.value = false
  setTimeout(() => {
    emit('close', props.id || '')
  }, 300) // Wait for animation
}

const icons = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ'
}

const iconLabels = {
  success: 'Success',
  error: 'Error',
  warning: 'Warning',
  info: 'Info'
}
</script>

<template>
  <Transition name="toast">
    <div
      v-if="visible"
      :class="['toast', `toast-${type}`]"
      role="alert"
      :aria-live="type === 'error' ? 'assertive' : 'polite'"
      :aria-label="iconLabels[type]"
    >
      <div class="toast-content">
        <span class="toast-icon" :aria-hidden="true">{{ icons[type] }}</span>
        <span class="toast-message">{{ message }}</span>
      </div>
      <button
        v-if="persistent"
        class="toast-close"
        @click="close"
        aria-label="Close notification"
      >
        <span aria-hidden="true">×</span>
      </button>
    </div>
  </Transition>
</template>

<style scoped>
.toast {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--vp-spacing-3);
  padding: var(--vp-spacing-3) var(--vp-spacing-4);
  border-radius: var(--vp-radius-md);
  box-shadow: var(--vp-shadow-lg);
  min-width: 300px;
  max-width: 500px;
  font-size: var(--vp-font-size-sm);
  line-height: var(--vp-line-height-normal);
  backdrop-filter: blur(8px);
  border: 1px solid;
  transition: all var(--vp-transition-base) var(--vp-ease-out);
}

.toast-content {
  display: flex;
  align-items: center;
  gap: var(--vp-spacing-2);
  flex: 1;
}

.toast-icon {
  font-size: var(--vp-font-size-lg);
  font-weight: var(--vp-font-weight-bold);
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
}

.toast-message {
  flex: 1;
  color: var(--vp-c-text-1);
}

.toast-close {
  background: transparent;
  border: none;
  color: var(--vp-c-text-2);
  cursor: pointer;
  font-size: var(--vp-font-size-xl);
  line-height: 1;
  padding: var(--vp-spacing-1);
  border-radius: var(--vp-radius-sm);
  transition: all var(--vp-transition-fast) var(--vp-ease-out);
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.toast-close:hover {
  background: rgba(0, 0, 0, 0.1);
  color: var(--vp-c-text-1);
}

.toast-close:focus-visible {
  outline: 2px solid var(--vp-c-brand);
  outline-offset: 2px;
}

/* Toast Types */
.toast-success {
  background: var(--vp-c-success-soft);
  border-color: var(--vp-c-success);
  color: var(--vp-c-success-dark);
}

.toast-success .toast-icon {
  background: var(--vp-c-success);
  color: white;
}

.toast-error {
  background: var(--vp-c-error-soft);
  border-color: var(--vp-c-error);
  color: var(--vp-c-error-dark);
}

.toast-error .toast-icon {
  background: var(--vp-c-error);
  color: white;
}

.toast-warning {
  background: var(--vp-c-warning-soft);
  border-color: var(--vp-c-warning);
  color: var(--vp-c-warning-dark);
}

.toast-warning .toast-icon {
  background: var(--vp-c-warning);
  color: white;
}

.toast-info {
  background: var(--vp-c-info-soft);
  border-color: var(--vp-c-info);
  color: var(--vp-c-info-dark);
}

.toast-info .toast-icon {
  background: var(--vp-c-info);
  color: white;
}

/* Animations */
.toast-enter-active,
.toast-leave-active {
  transition: all var(--vp-transition-base) var(--vp-ease-out);
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%) scale(0.95);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%) scale(0.95);
}

/* Dark mode adjustments */
.dark .toast-close:hover {
  background: rgba(255, 255, 255, 0.1);
}

/* Mobile responsiveness */
@media (max-width: 640px) {
  .toast {
    min-width: auto;
    max-width: calc(100vw - var(--vp-spacing-8));
  }
}
</style>
