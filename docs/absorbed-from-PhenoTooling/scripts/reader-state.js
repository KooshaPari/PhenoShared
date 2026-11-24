// Per READER_MODE.md spec:
// - Trigger: R key (global), Reader toggle click, prefers-reduced-motion: reduce (if user hasn't toggled before)
// - Exit: R key, toggle click, Esc; resizing preserves the visitor's choice
// - DOM: html[data-reader="true"] applied globally
// - Persistence: localStorage reads/writes

let readerMode = false;
let readers = new Set();
let initReady = false;

function announce(message) {
  const region = document.getElementById('announcements');
  if (region) region.textContent = message;
}

function applyReaderMode(on = true) {
  readerMode = on;
  document.documentElement.dataset.reader = on ? 'true' : 'false';

  const announcement = on ? 'Reader mode active' : 'Reader mode inactive';
  announce(announcement);

  // Focus management per spec
  if (on) {
    const firstHeading = document.querySelector('#view-root h1, #view-root h2');
    firstHeading?.setAttribute('tabindex', '-1');
    firstHeading?.focus?.();
  } else {
    document.getElementById('reader-toggle')?.focus?.();
  }

  for (const subscriber of readers) subscriber(readerMode);
}

function initReader() {
  if (initReady) return;
  initReady = true;
  try {
    readerMode = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch { /* retain default when media queries are unavailable */ }
  try {
    const saved = localStorage.getItem('koosha-atelier-reader');
    if (saved === 'true' || saved === 'false') readerMode = saved === 'true';
  } catch { /* storage can be unavailable */ }
  document.documentElement.dataset.reader = String(readerMode);

  // Ensure live region exists
  if (!document.getElementById('announcements')) {
    const region = document.createElement('div');
    region.id = 'announcements';
    region.setAttribute('role', 'status');
    region.setAttribute('aria-live', 'polite');
    region.style.cssText = `
      position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
      overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0;
    `;
    document.body.appendChild(region);
  }

  // Keyboard handler: R key (global, not in input)
  document.addEventListener('keydown', (e) => {
    if (e.defaultPrevented || e.isComposing || e.repeat || e.ctrlKey || e.metaKey || e.altKey ||
        e.target?.isContentEditable || e.target?.closest?.('input, textarea, select, [role="textbox"]')) return;
    if (e.key.toLowerCase() === 'r') {
      e.preventDefault();
      toggleReader();
    }
  });

  // Escape exits Reader Mode
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && readerMode && !e.defaultPrevented) {
      applyReaderMode(false);
      persistReader();
    }
  });

  // Resizing must not override the visitor's Reader preference.
}

function toggleReader() {
  applyReaderMode(!readerMode);
  persistReader();
}

function persistReader() {
  // Persist user choice
  try {
    localStorage.setItem('koosha-atelier-reader', readerMode.toString());
    localStorage.setItem('koosha-atelier-reader-toggled', 'true');
  } catch {
    /* ignore */
  }
}

export function createReaderState() {
  initReader();

  return {
    get() {
      return readerMode;
    },

    set(value) {
      applyReaderMode(Boolean(value));
      persistReader();
    },

    toggle() {
      toggleReader();
    },

    subscribe(subscriber) {
      readers.add(subscriber);
      return () => readers.delete(subscriber);
    },

    // Called from lensState.subscribe for sync
    syncWithLens(lensState) {
      return lensState.subscribe((lens) => {
        // In Reader Mode, lens toggle still works; nothing extra needed here
      });
    },
  };
}
