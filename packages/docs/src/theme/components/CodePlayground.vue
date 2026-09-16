<script setup lang="ts">
import { ref, onMounted, onUnmounted, inject } from 'vue'
import LoadingSpinner from './LoadingSpinner.vue'

const props = defineProps<{
  lang?: string
  endpoint?: string
  code: string
  title?: string
}>()

const output = ref('')
const running = ref(false)
const error = ref('')
const showOutput = ref(false)
const copied = ref(false)
const outputCollapsed = ref(false)

// Inject toast if available
const toast = inject<{
  success: (message: string) => void
  error: (message: string) => void
} | null>('toast', null)

async function run() {
  running.value = true
  error.value = ''
  output.value = ''
  showOutput.value = false
  outputCollapsed.value = false

  try {
    // Simulate execution with timeout handling
    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(() => reject(new Error('Execution timeout')), 10000)
    )

    const executionPromise = new Promise(resolve => {
      setTimeout(() => {
        if (props.lang === 'python' || !props.lang) {
          resolve('Execution simulated. Connect to API endpoint for real execution.')
        } else {
          resolve(`Simulated ${props.lang} execution`)
        }
      }, 500)
    })

    const result = await Promise.race([executionPromise, timeoutPromise])
    output.value = String(result)
    showOutput.value = true

    if (toast) {
      toast.success('Code executed successfully')
    }
  } catch (e) {
    const errorMessage = e instanceof Error ? e.message : String(e)
    error.value = errorMessage
    showOutput.value = true

    if (toast) {
      toast.error(`Execution failed: ${errorMessage}`)
    }
  } finally {
    running.value = false
  }
}

async function copyCode() {
  try {
    await navigator.clipboard.writeText(props.code)
    copied.value = true
    if (toast) {
      toast.success('Code copied to clipboard')
    }
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (e) {
    if (toast) {
      toast.error('Failed to copy code')
    }
  }
}

function toggleOutput() {
  outputCollapsed.value = !outputCollapsed.value
}

// Keyboard shortcuts
function handleKeydown(event: KeyboardEvent) {
  // Ctrl+Enter or Cmd+Enter to run
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
    event.preventDefault()
    if (!running.value) {
      run()
    }
  }

  // Ctrl+C to copy (only if not in input)
  if ((event.ctrlKey || event.metaKey) && event.key === 'c' && !(event.target instanceof HTMLInputElement)) {
    // Allow default copy behavior
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div
    class="code-playground"
    role="region"
    :aria-label="title || 'Code playground'"
  >
    <div class="code-playground-header">
      <div class="header-left">
        <span v-if="title" class="playground-title">{{ title }}</span>
        <span class="lang-badge" :aria-label="`Language: ${lang || 'python'}`">
          {{ lang || 'python' }}
        </span>
      </div>
      <div class="header-right">
        <button
          @click="copyCode"
          class="action-button copy-button"
          :class="{ copied: copied }"
          :aria-label="copied ? 'Copied!' : 'Copy code'"
          :title="copied ? 'Copied!' : 'Copy code (Ctrl+C)'"
        >
          <span v-if="copied" class="icon">✓</span>
          <span v-else class="icon">📋</span>
        </button>
        <button
          @click="run"
          :disabled="running"
          class="action-button run-button"
          :aria-label="running ? 'Running...' : 'Run code'"
          :title="running ? 'Running...' : 'Run code (Ctrl+Enter)'"
        >
          <LoadingSpinner v-if="running" size="sm" variant="spinner" />
          <span v-else class="icon">▶</span>
          <span class="button-text">{{ running ? 'Running...' : 'Run' }}</span>
        </button>
      </div>
    </div>

    <div class="code-container">
      <pre><code>{{ code }}</code></pre>
    </div>

    <Transition name="output">
      <div v-if="showOutput && (output || error)" class="output-section">
        <button
          v-if="output || error"
          @click="toggleOutput"
          class="output-toggle"
          :aria-expanded="!outputCollapsed"
          aria-controls="output-content"
        >
          <span class="output-header">
            {{ error ? 'Error' : 'Output' }}
          </span>
          <span class="toggle-icon" :class="{ collapsed: outputCollapsed }">▼</span>
        </button>
        <div
          v-show="!outputCollapsed"
          id="output-content"
          class="output-content"
          :class="{ error: error }"
        >
          <pre v-if="error" class="error-output">{{ error }}</pre>
          <pre v-else class="success-output">{{ output }}</pre>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.code-playground {
  border: 1px solid var(--vp-c-divider);
  border-radius: var(--vp-radius-md);
  margin: var(--vp-spacing-6) 0;
  overflow: hidden;
  background: var(--vp-c-bg-soft);
  box-shadow: var(--vp-shadow-sm);
  transition: box-shadow var(--vp-transition-base) var(--vp-ease-out);
}

.code-playground:hover {
  box-shadow: var(--vp-shadow-md);
}

.code-playground-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--vp-spacing-3) var(--vp-spacing-4);
  background: var(--vp-c-bg);
  border-bottom: 1px solid var(--vp-c-divider);
  gap: var(--vp-spacing-3);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--vp-spacing-2);
  flex: 1;
  min-width: 0;
}

.playground-title {
  font-weight: var(--vp-font-weight-semibold);
  font-size: var(--vp-font-size-sm);
  color: var(--vp-c-text-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.lang-badge {
  font-size: var(--vp-font-size-xs);
  padding: var(--vp-spacing-1) var(--vp-spacing-2);
  background: var(--vp-c-bg-alt);
  border-radius: var(--vp-radius-sm);
  color: var(--vp-c-text-2);
  font-family: var(--vp-font-family-mono);
  font-weight: var(--vp-font-weight-medium);
  white-space: nowrap;
  flex-shrink: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--vp-spacing-2);
  flex-shrink: 0;
}

.action-button {
  display: flex;
  align-items: center;
  gap: var(--vp-spacing-1);
  padding: var(--vp-spacing-2) var(--vp-spacing-3);
  border: 1px solid var(--vp-c-divider);
  background: var(--vp-c-bg);
  color: var(--vp-c-text-2);
  border-radius: var(--vp-radius-sm);
  cursor: pointer;
  font-size: var(--vp-font-size-sm);
  font-weight: var(--vp-font-weight-medium);
  transition: all var(--vp-transition-fast) var(--vp-ease-out);
  white-space: nowrap;
  min-height: 32px;
}

.action-button:hover:not(:disabled) {
  background: var(--vp-c-bg-alt);
  color: var(--vp-c-text-1);
  border-color: var(--vp-c-divider);
  transform: translateY(-1px);
}

.action-button:active:not(:disabled) {
  transform: translateY(0);
}

.action-button:focus-visible {
  outline: 2px solid var(--vp-c-brand);
  outline-offset: 2px;
}

.action-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.copy-button {
  padding: var(--vp-spacing-2);
  min-width: 32px;
  justify-content: center;
}

.copy-button.copied {
  background: var(--vp-c-success-soft);
  border-color: var(--vp-c-success);
  color: var(--vp-c-success-dark);
}

.run-button {
  border-color: var(--vp-c-brand);
  background: var(--vp-c-brand);
  color: white;
  padding: var(--vp-spacing-2) var(--vp-spacing-4);
}

.run-button:hover:not(:disabled) {
  background: var(--vp-c-brand-dark);
  border-color: var(--vp-c-brand-dark);
  color: white;
}

.run-button .icon {
  font-size: var(--vp-font-size-sm);
  line-height: 1;
}

.button-text {
  font-size: var(--vp-font-size-sm);
}

.code-container {
  padding: var(--vp-spacing-4);
  background: var(--vp-c-bg);
  overflow-x: auto;
  position: relative;
}

.code-container pre {
  margin: 0;
  padding: 0;
  background: transparent;
}

.code-container code {
  font-family: var(--vp-font-family-mono);
  font-size: var(--vp-font-size-sm);
  line-height: var(--vp-line-height-relaxed);
  color: var(--vp-c-text-1);
}

.output-section {
  border-top: 1px solid var(--vp-c-divider);
  background: var(--vp-c-bg-soft);
}

.output-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--vp-spacing-3) var(--vp-spacing-4);
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--vp-c-text-1);
  font-size: var(--vp-font-size-sm);
  font-weight: var(--vp-font-weight-semibold);
  transition: background var(--vp-transition-fast) var(--vp-ease-out);
}

.output-toggle:hover {
  background: rgba(0, 0, 0, 0.05);
}

.dark .output-toggle:hover {
  background: rgba(255, 255, 255, 0.05);
}

.output-toggle:focus-visible {
  outline: 2px solid var(--vp-c-brand);
  outline-offset: -2px;
}

.output-header {
  display: flex;
  align-items: center;
  gap: var(--vp-spacing-2);
}

.toggle-icon {
  transition: transform var(--vp-transition-base) var(--vp-ease-out);
  font-size: var(--vp-font-size-xs);
  color: var(--vp-c-text-2);
}

.toggle-icon.collapsed {
  transform: rotate(-90deg);
}

.output-content {
  padding: var(--vp-spacing-4);
  max-height: 400px;
  overflow-y: auto;
}

.output-content.error {
  background: var(--vp-c-error-soft);
}

.output-content pre {
  margin: 0;
  font-family: var(--vp-font-family-mono);
  font-size: var(--vp-font-size-sm);
  line-height: var(--vp-line-height-relaxed);
  white-space: pre-wrap;
  word-break: break-word;
}

.success-output {
  color: var(--vp-c-text-1);
}

.error-output {
  color: var(--vp-c-error-dark);
}

/* Animations */
.output-enter-active,
.output-leave-active {
  transition: all var(--vp-transition-base) var(--vp-ease-out);
}

.output-enter-from,
.output-leave-to {
  opacity: 0;
  max-height: 0;
  overflow: hidden;
}

/* Mobile responsiveness */
@media (max-width: 640px) {
  .code-playground-header {
    flex-wrap: wrap;
    gap: var(--vp-spacing-2);
  }

  .header-left {
    width: 100%;
  }

  .header-right {
    width: 100%;
    justify-content: flex-end;
  }

  .playground-title {
    font-size: var(--vp-font-size-xs);
  }

  .action-button {
    padding: var(--vp-spacing-1) var(--vp-spacing-2);
    font-size: var(--vp-font-size-xs);
  }

  .button-text {
    display: none;
  }
}
</style>
