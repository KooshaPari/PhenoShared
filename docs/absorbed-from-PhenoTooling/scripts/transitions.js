/**
 * Page Transition Engine
 *
 * Hooks into the router's `routechange` CustomEvent and wraps the
 * app's render call with coordinated fade-out / fade-in animations.
 *
 * Usage:
 *   import { initTransitions } from './transitions.js';
 *   initTransitions(router, { render });
 *
 * The engine is non-destructive: if JS is disabled or the CSS View
 * Transitions API is available, the appropriate path is taken.
 */

/* ── Timing constants ──────────────────────────────────────────────── */

const DURATION_OUT = 180;   // ms  –  fade / slide out
const DURATION_IN = 250;    // ms  –  fade / slide in
const DEBOUNCE_MS = 100;    // ms  –  rapid-navigation guard

/* ── Lifecycle hooks ───────────────────────────────────────────────── */

/** @type {Array<(route: object) => void | Promise<void>>} */
const _beforeCallbacks = [];

/** @type {Array<(route: object) => void | Promise<void>>} */
const _afterCallbacks = [];

/* ── Helpers ───────────────────────────────────────────────────────── */

function prefersReducedMotion() {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
}

function viewTransitionsSupported() {
  return 'startViewTransition' in document;
}

/** Wait for the next frame so the browser has time to paint. */
function nextFrame() {
  return new Promise((resolve) => requestAnimationFrame(() => resolve()));
}

/** Promise-based delay. */
function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Run an array of callbacks sequentially, awaiting each. */
async function runCallbacks(list, arg) {
  for (const cb of list) {
    await cb(arg);
  }
}

/* ── Core transition helpers ───────────────────────────────────────── */

/**
 * Animate the current page out.
 * Returns a Promise that resolves once the old content is hidden.
 *
 * @param {HTMLElement} container – the view-root element
 * @returns {Promise<void>}
 */
export function transitionOut(container) {
  return new Promise((resolve) => {
    if (prefersReducedMotion()) {
      container.innerHTML = '';
      return resolve();
    }

    container.classList.add('view-transition-preparing', 'view-transition-out');

    // Listen for the transition end, but fall back to timeout so we
    // never get stuck.
    const onEnd = () => {
      container.removeEventListener('transitionend', onEnd);
      container.innerHTML = '';
      container.classList.remove('view-transition-out');
      resolve();
    };

    container.addEventListener('transitionend', onEnd, { once: true });
    setTimeout(onEnd, DURATION_OUT + 30);   // safety net
  });
}

/**
 * Inject new HTML into the container and animate it in.
 * Returns a Promise that resolves once the new content is fully visible.
 *
 * @param {HTMLElement} container – the view-root element
 * @param {string} newHTML – raw HTML string to inject
 * @returns {Promise<void>}
 */
export function transitionIn(container, newHTML) {
  return new Promise(async (resolve) => {
    if (prefersReducedMotion()) {
      container.innerHTML = newHTML;
      container.classList.remove('view-transition-preparing', 'view-transition-in');
      return resolve();
    }

    // Inject content in the invisible state
    container.innerHTML = newHTML;
    container.classList.remove('view-transition-out');
    container.classList.add('view-transition-in');

    // Let the browser paint the initial invisible state, then flip
    await nextFrame();
    container.classList.add('is-visible');

    const onEnd = () => {
      container.removeEventListener('transitionend', onEnd);
      container.classList.remove('view-transition-in', 'is-visible', 'view-transition-preparing');
      resolve();
    };

    container.addEventListener('transitionend', onEnd, { once: true });
    setTimeout(onEnd, DURATION_IN + 30);    // safety net
  });
}

/* ── Native CSS View Transitions path ──────────────────────────────── */

/**
 * Wrap a render call in the native CSS View Transitions API
 * (startViewTransition).
 *
 * @param {HTMLElement} viewRoot
 * @param {() => void} renderFn
 */
function nativeTransition(viewRoot, renderFn) {
  document.startViewTransition(() => {
    renderFn();
  });
}

/* ── Debounce / queue guard ────────────────────────────────────────── */

let _transitionQueue = null;   // active in-flight transition Promise
let _pendingRoute = null;      // latest route while a transition is running
let _timerId = null;

/* ── Public API ────────────────────────────────────────────────────── */

/**
 * Initialise the transition engine and hook it into the router.
 *
 * @param {object}   _router      – reserved for future router-specific hooks
 * @param {{ render: () => void, viewRoot?: HTMLElement }} options
 * @returns {{ destroy: () => void }} – teardown handle
 */
export function initTransitions(_router, { render: renderFn, viewRoot } = {}) {
  const root = viewRoot || document.getElementById('view-root');
  if (!root || typeof renderFn !== 'function') {
    console.warn('[transitions] initTransitions requires a render function and a #view-root');
    return { destroy() {} };
  }

  /**
   * Handle a single navigation: run before-callbacks → transition-out →
   * render → transition-in → after-callbacks.
   *
   * When a newer navigation arrives while one is in flight we skip the
   * full transition and jump to the pending route to avoid stacking
   * animations.
   */
  async function handleNavigation(route) {
    // If a transition is already in flight, just record the latest route
    if (_transitionQueue) {
      _pendingRoute = route;
      return;
    }

    _pendingRoute = null;

    // Before-navigate hooks
    await runCallbacks(_beforeCallbacks, route);

    // Choose transition strategy
    if (prefersReducedMotion() || !viewTransitionsSupported()) {
      // Manual path
      await transitionOut(root);
      renderFn();
      await transitionIn(root, '');
    } else {
      // Native view-transition path
      nativeTransition(root, () => {
        renderFn();
      });
    }

    // After-navigate hooks
    await runCallbacks(_afterCallbacks, route);

    // Check if a newer navigation arrived during the transition
    if (_pendingRoute) {
      const next = _pendingRoute;
      _pendingRoute = null;
      _transitionQueue = null;
      handleNavigation(next);
    } else {
      _transitionQueue = null;
    }
  }

  /** Debounced entry point wired to the router event. */
  function onRouteChange(event) {
    const route = event.detail;
    clearTimeout(_timerId);
    _timerId = setTimeout(() => {
      handleNavigation(route);
    }, DEBOUNCE_MS);
  }

  window.addEventListener('routechange', onRouteChange);

  return {
    destroy() {
      window.removeEventListener('routechange', onRouteChange);
      clearTimeout(_timerId);
      _transitionQueue = null;
      _pendingRoute = null;
    },
  };
}

/**
 * Register a callback that runs before the page-out animation starts.
 * The callback receives the incoming route object.
 *
 * @param {(route: object) => void | Promise<void>} callback
 */
export function onBeforeNavigate(callback) {
  _beforeCallbacks.push(callback);
}

/**
 * Register a callback that runs after the new page has fully faded in.
 * The callback receives the new route object.
 *
 * @param {(route: object) => void | Promise<void>} callback
 */
export function onAfterNavigate(callback) {
  _afterCallbacks.push(callback);
}
