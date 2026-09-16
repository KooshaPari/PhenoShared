<script setup lang="ts">
import { ref, onMounted, onErrorCaptured } from 'vue'
import LoadingSpinner from './LoadingSpinner.vue'

const props = defineProps({
  src: {
    type: String,
    required: true
  },
  alt: {
    type: String,
    default: 'Demo'
  },
  caption: {
    type: String,
    default: ''
  },
  lazy: {
    type: Boolean,
    default: true
  },
  expandable: {
    type: Boolean,
    default: true
  }
})

const fullSrc = ref('')
const loading = ref(true)
const error = ref(false)
const expanded = ref(false)
const imageLoaded = ref(false)

onMounted(() => {
  // src is expected to be something like "cli-demo.gif"
  // We prepend the assets path
  fullSrc.value = `/assets/demos/${props.src}`

  // If not lazy, load immediately
  if (!props.lazy) {
    preloadImage()
  }
})

function preloadImage() {
  const img = new Image()
  img.onload = () => {
    loading.value = false
    imageLoaded.value = true
  }
  img.onerror = () => {
    loading.value = false
    error.value = true
  }
  img.src = fullSrc.value
}

function handleIntersection(entries: IntersectionObserverEntry[]) {
  entries.forEach(entry => {
    if (entry.isIntersecting && props.lazy && loading.value) {
      preloadImage()
    }
  })
}

onMounted(() => {
  if (props.lazy && typeof window !== 'undefined' && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(handleIntersection, {
      rootMargin: '50px'
    })

    const container = document.querySelector(`[data-demo-gif="${props.src}"]`)
    if (container) {
      observer.observe(container)
    }

    return () => observer.disconnect()
  }
})

function toggleExpand() {
  if (props.expandable) {
    expanded.value = !expanded.value
  }
}

onErrorCaptured(() => {
  error.value = true
  loading.value = false
  return false
})
</script>

<template>
  <div
    :data-demo-gif="src"
    class="demo-gif-container"
    :class="{ expandable: expandable && !error, expanded: expanded }"
  >
    <div
      class="demo-gif-wrapper"
      :class="{ loading: loading, error: error }"
      @click="toggleExpand"
    >
      <!-- Loading State -->
      <div v-if="loading" class="demo-gif-loading">
        <LoadingSpinner size="md" variant="spinner" />
        <span class="loading-text">Loading demo...</span>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="demo-gif-error">
        <span class="error-icon">⚠️</span>
        <span class="error-text">Failed to load demo</span>
        <button
          class="retry-button"
          @click.stop="preloadImage"
          aria-label="Retry loading demo"
        >
          Retry
        </button>
      </div>

      <!-- Image -->
      <Transition name="fade">
        <img
          v-if="imageLoaded && !error"
          :src="fullSrc"
          :alt="alt"
          class="demo-gif"
          :class="{ clickable: expandable }"
          loading="lazy"
          @load="loading = false; imageLoaded = true"
          @error="error = true; loading = false"
        />
      </Transition>

      <!-- Expand Indicator -->
      <div
        v-if="expandable && imageLoaded && !error"
        class="expand-indicator"
        aria-hidden="true"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
        </svg>
      </div>
    </div>

    <!-- Caption -->
    <p v-if="caption && !loading" class="demo-gif-caption">
      {{ caption }}
    </p>

    <!-- Expanded Modal -->
    <Transition name="modal">
      <div
        v-if="expanded && expandable"
        class="demo-gif-modal"
        @click="expanded = false"
      >
        <div class="modal-content" @click.stop>
          <button
            class="modal-close"
            @click="expanded = false"
            aria-label="Close expanded view"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
          <img
            :src="fullSrc"
            :alt="alt"
            class="modal-image"
          />
          <p v-if="caption" class="modal-caption">{{ caption }}</p>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.demo-gif-container {
  margin: var(--vp-spacing-8) 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.demo-gif-wrapper {
  position: relative;
  border-radius: var(--vp-radius-md);
  overflow: hidden;
  box-shadow: var(--vp-shadow-lg);
  border: 1px solid var(--vp-c-divider);
  background: var(--vp-c-bg-soft);
  width: 100%;
  max-width: 100%;
  transition: all var(--vp-transition-base) var(--vp-ease-out);
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.demo-gif-wrapper:hover {
  box-shadow: var(--vp-shadow-xl);
}

.demo-gif-wrapper.expandable {
  cursor: pointer;
}

.demo-gif-wrapper.loading {
  min-height: 300px;
}

.demo-gif-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--vp-spacing-3);
  padding: var(--vp-spacing-8);
  color: var(--vp-c-text-2);
}

.loading-text {
  font-size: var(--vp-font-size-sm);
  color: var(--vp-c-text-2);
}

.demo-gif-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--vp-spacing-3);
  padding: var(--vp-spacing-8);
  color: var(--vp-c-error);
}

.error-icon {
  font-size: var(--vp-font-size-2xl);
}

.error-text {
  font-size: var(--vp-font-size-sm);
  color: var(--vp-c-error);
}

.retry-button {
  padding: var(--vp-spacing-2) var(--vp-spacing-4);
  background: var(--vp-c-error);
  color: white;
  border: none;
  border-radius: var(--vp-radius-sm);
  cursor: pointer;
  font-size: var(--vp-font-size-sm);
  font-weight: var(--vp-font-weight-medium);
  transition: all var(--vp-transition-fast) var(--vp-ease-out);
}

.retry-button:hover {
  background: var(--vp-c-error-dark);
  transform: translateY(-1px);
}

.retry-button:focus-visible {
  outline: 2px solid var(--vp-c-error);
  outline-offset: 2px;
}

.demo-gif {
  display: block;
  width: 100%;
  height: auto;
  transition: transform var(--vp-transition-base) var(--vp-ease-out);
}

.demo-gif.clickable {
  cursor: zoom-in;
}

.demo-gif-wrapper.expandable:hover .demo-gif.clickable {
  transform: scale(1.02);
}

.expand-indicator {
  position: absolute;
  top: var(--vp-spacing-2);
  right: var(--vp-spacing-2);
  width: 32px;
  height: 32px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  border-radius: var(--vp-radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity var(--vp-transition-base) var(--vp-ease-out);
  pointer-events: none;
}

.demo-gif-wrapper.expandable:hover .expand-indicator {
  opacity: 1;
}

.expand-indicator svg {
  width: 18px;
  height: 18px;
}

.demo-gif-caption {
  margin-top: var(--vp-spacing-3);
  font-size: var(--vp-font-size-sm);
  color: var(--vp-c-text-2);
  font-style: italic;
  text-align: center;
  max-width: 100%;
}

/* Modal */
.demo-gif-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: var(--vp-z-modal);
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--vp-spacing-4);
  cursor: pointer;
}

.modal-content {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
  background: var(--vp-c-bg);
  border-radius: var(--vp-radius-lg);
  box-shadow: var(--vp-shadow-xl);
  overflow: auto;
  cursor: default;
}

.modal-close {
  position: absolute;
  top: var(--vp-spacing-2);
  right: var(--vp-spacing-2);
  width: 40px;
  height: 40px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  border: none;
  border-radius: var(--vp-radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--vp-transition-fast) var(--vp-ease-out);
  z-index: 1;
}

.modal-close:hover {
  background: rgba(0, 0, 0, 0.8);
  transform: scale(1.1);
}

.modal-close:focus-visible {
  outline: 2px solid white;
  outline-offset: 2px;
}

.modal-close svg {
  width: 20px;
  height: 20px;
}

.modal-image {
  display: block;
  width: 100%;
  height: auto;
  max-width: 100%;
}

.modal-caption {
  padding: var(--vp-spacing-4);
  font-size: var(--vp-font-size-sm);
  color: var(--vp-c-text-2);
  text-align: center;
  border-top: 1px solid var(--vp-c-divider);
}

/* Animations */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--vp-transition-base) var(--vp-ease-out);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity var(--vp-transition-base) var(--vp-ease-out);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-content {
  animation: modal-scale-in var(--vp-transition-base) var(--vp-ease-out);
}

@keyframes modal-scale-in {
  from {
    transform: scale(0.9);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

/* Dark mode adjustments */
.dark .demo-gif-wrapper {
  box-shadow: var(--vp-shadow-xl);
}

.dark .expand-indicator {
  background: rgba(255, 255, 255, 0.2);
}

.dark .modal-close {
  background: rgba(255, 255, 255, 0.2);
}

.dark .modal-close:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* Mobile responsiveness */
@media (max-width: 640px) {
  .demo-gif-container {
    margin: var(--vp-spacing-6) 0;
  }

  .demo-gif-wrapper {
    min-height: 150px;
  }

  .demo-gif-wrapper.loading {
    min-height: 200px;
  }

  .expand-indicator {
    width: 28px;
    height: 28px;
    top: var(--vp-spacing-1);
    right: var(--vp-spacing-1);
  }

  .expand-indicator svg {
    width: 16px;
    height: 16px;
  }

  .modal-content {
    max-width: 95vw;
    max-height: 95vh;
  }

  .modal-close {
    width: 36px;
    height: 36px;
  }
}
</style>
