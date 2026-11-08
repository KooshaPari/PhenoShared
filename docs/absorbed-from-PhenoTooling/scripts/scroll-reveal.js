/* ================================================================
   Scroll-reveal — IntersectionObserver-based reveal system.

   Attributes:
     data-reveal         Direction/variant: left|right|up|down|fade|scale|rotate
     data-reveal-delay   Stagger delay in ms (set via CSS transition-delay)
     data-reveal-distance  Custom slide distance in px (default 24)

   CSS classes:
     .reveal-hidden  — initial off-screen state (set by CSS per data-reveal)
     .reveal-visible — animated final state

   Usage:
     import { initScrollReveal, refreshObserver } from './scroll-reveal.js';
     initScrollReveal();  // call once at app start
     refreshObserver();   // call after SPA route change to rescan DOM
   ================================================================ */

const SELECTOR = '[data-reveal]';
const DEFAULT_DISTANCE = 24;

let _observer = null;
let _mutationObserver = null;
let _rafId = 0;
let _initialized = false;

/* ------------------------------------------------------------------
   Reduced-motion detection
   ------------------------------------------------------------------ */
function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/* ------------------------------------------------------------------
   Apply initial hidden state to an element based on its data-reveal
   ------------------------------------------------------------------ */
function applyHiddenState(el) {
  const distance = parseInt(el.dataset.revealDistance, 10) || DEFAULT_DISTANCE;

  // Set custom distance as CSS custom property so CSS can use it
  if (distance !== DEFAULT_DISTANCE) {
    el.style.setProperty('--reveal-distance', `${distance}px`);
  }
}

/* ------------------------------------------------------------------
   Apply stagger delay from data-reveal-delay
   ------------------------------------------------------------------ */
function applyDelay(el) {
  const delay = parseInt(el.dataset.revealDelay, 10);
  if (!isNaN(delay) && delay > 0) {
    el.style.transitionDelay = `${delay}ms`;
  }
}

/* ------------------------------------------------------------------
   Reveal a single element
   ------------------------------------------------------------------ */
function revealElement(el) {
  if (el.classList.contains('reveal-visible')) return;

  applyDelay(el);
  el.classList.remove('reveal-hidden');
  el.classList.add('reveal-visible');
}

/* ------------------------------------------------------------------
   Scan DOM for new [data-reveal] elements and add .reveal-hidden
   ------------------------------------------------------------------ */
function scanForRevealElements(root = document) {
  const elements = root.querySelectorAll(SELECTOR);
  for (const el of elements) {
    if (prefersReducedMotion()) {
      // Show immediately, skip animation entirely
      el.classList.remove('reveal-hidden');
      el.classList.add('reveal-visible');
    } else if (!el.classList.contains('reveal-visible') && !el.classList.contains('reveal-hidden')) {
      el.classList.add('reveal-hidden');
      applyHiddenState(el);
    }
  }
}

/* ------------------------------------------------------------------
   Batch DOM scan via requestAnimationFrame
   ------------------------------------------------------------------ */
function batchScan(root = document) {
  if (_rafId) cancelAnimationFrame(_rafId);
  _rafId = requestAnimationFrame(() => {
    scanForRevealElements(root);
    attachToObserver(root);
  });
}

/* ------------------------------------------------------------------
   Observe elements for intersection (viewport entry)
   ------------------------------------------------------------------ */
function attachToObserver(root = document) {
  if (!_observer) return;
  const elements = root.querySelectorAll(
    `${SELECTOR}:not(.reveal-visible):not(.reveal-hidden)`
  );
  for (const el of elements) {
    _observer.observe(el);
  }
  // Also observe elements that are .reveal-hidden but not yet observed
  const hiddenElements = root.querySelectorAll(
    `${SELECTOR}.reveal-hidden`
  );
  for (const el of hiddenElements) {
    _observer.observe(el);
  }
}

/* ------------------------------------------------------------------
   Create the IntersectionObserver
   ------------------------------------------------------------------ */
function createObserver() {
  if (_observer) _observer.disconnect();

  _observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          revealElement(entry.target);
          _observer.unobserve(entry.target);
        }
      }
    },
    {
      threshold: 0.1,
      rootMargin: '0px 0px -40px 0px',
    }
  );
}

/* ------------------------------------------------------------------
   Create MutationObserver for dynamically added elements
   ------------------------------------------------------------------ */
function createMutationObserver() {
  if (_mutationObserver) _mutationObserver.disconnect();

  _mutationObserver = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (node.nodeType !== Node.ELEMENT_NODE) continue;
        if (node.matches?.(SELECTOR) || node.querySelector?.(SELECTOR)) {
          batchScan(node);
        }
      }
    }
  });

  _mutationObserver.observe(document.body, {
    childList: true,
    subtree: true,
  });
}

/* ------------------------------------------------------------------
   Public API
   ------------------------------------------------------------------ */

/**
 * Initialize the scroll-reveal system.
 * Safe to call multiple times; subsequent calls act as a refresh.
 */
export function initScrollReveal() {
  if (_initialized) {
    refreshObserver();
    return;
  }
  _initialized = true;

  createObserver();
  createMutationObserver();
  batchScan();
}

/**
 * Rescan the DOM for new [data-reveal] elements.
 * Call after SPA route changes or dynamic content injection.
 */
export function refreshObserver() {
  batchScan();
}

export default initScrollReveal;
