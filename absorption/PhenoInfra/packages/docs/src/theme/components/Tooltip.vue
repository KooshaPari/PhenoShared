<script setup lang="ts">
import { ref, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{
  content: string
  position?: 'top' | 'bottom' | 'left' | 'right'
  delay?: number
}>(), {
  position: 'top',
  delay: 200
})

const visible = ref(false)
const timer = ref<number | null>(null)

function show() {
  if (timer.value) {
    clearTimeout(timer.value)
  }
  timer.value = window.setTimeout(() => {
    visible.value = true
  }, props.delay)
}

function hide() {
  if (timer.value) {
    clearTimeout(timer.value)
    timer.value = null
  }
  visible.value = false
}

onUnmounted(() => {
  if (timer.value) {
    clearTimeout(timer.value)
  }
})
</script>

<template>
  <span
    class="tooltip-wrapper"
    @mouseenter="show"
    @mouseleave="hide"
    @focus="show"
    @blur="hide"
  >
    <slot />
    <Transition name="tooltip">
      <div
        v-if="visible"
        class="tooltip"
        :class="`tooltip-${position}`"
        role="tooltip"
      >
        {{ content }}
      </div>
    </Transition>
  </span>
</template>

<style scoped>
.tooltip-wrapper {
  position: relative;
  display: inline-block;
  cursor: help;
}

.tooltip {
  position: absolute;
  z-index: var(--vp-z-tooltip);
  padding: var(--vp-spacing-2) var(--vp-spacing-3);
  background: var(--vp-c-text-1);
  color: var(--vp-c-bg);
  border-radius: var(--vp-radius-sm);
  font-size: var(--vp-font-size-xs);
  line-height: var(--vp-line-height-normal);
  white-space: nowrap;
  box-shadow: var(--vp-shadow-lg);
  pointer-events: none;
  max-width: 250px;
  word-wrap: break-word;
  white-space: normal;
}

.tooltip-top {
  bottom: calc(100% + var(--vp-spacing-2));
  left: 50%;
  transform: translateX(-50%);
}

.tooltip-top::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 4px solid transparent;
  border-top-color: var(--vp-c-text-1);
}

.tooltip-bottom {
  top: calc(100% + var(--vp-spacing-2));
  left: 50%;
  transform: translateX(-50%);
}

.tooltip-bottom::after {
  content: '';
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 4px solid transparent;
  border-bottom-color: var(--vp-c-text-1);
}

.tooltip-left {
  right: calc(100% + var(--vp-spacing-2));
  top: 50%;
  transform: translateY(-50%);
}

.tooltip-left::after {
  content: '';
  position: absolute;
  left: 100%;
  top: 50%;
  transform: translateY(-50%);
  border: 4px solid transparent;
  border-left-color: var(--vp-c-text-1);
}

.tooltip-right {
  left: calc(100% + var(--vp-spacing-2));
  top: 50%;
  transform: translateY(-50%);
}

.tooltip-right::after {
  content: '';
  position: absolute;
  right: 100%;
  top: 50%;
  transform: translateY(-50%);
  border: 4px solid transparent;
  border-right-color: var(--vp-c-text-1);
}

/* Animations */
.tooltip-enter-active,
.tooltip-leave-active {
  transition: opacity var(--vp-transition-fast) var(--vp-ease-out),
    transform var(--vp-transition-fast) var(--vp-ease-out);
}

.tooltip-enter-from,
.tooltip-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.tooltip-top.tooltip-enter-from,
.tooltip-top.tooltip-leave-to {
  transform: translateX(-50%) translateY(4px);
}

.tooltip-bottom.tooltip-enter-from,
.tooltip-bottom.tooltip-leave-to {
  transform: translateX(-50%) translateY(-4px);
}

.tooltip-left.tooltip-enter-from,
.tooltip-left.tooltip-leave-to {
  transform: translateY(-50%) translateX(4px);
}

.tooltip-right.tooltip-enter-from,
.tooltip-right.tooltip-leave-to {
  transform: translateY(-50%) translateX(-4px);
}
</style>
