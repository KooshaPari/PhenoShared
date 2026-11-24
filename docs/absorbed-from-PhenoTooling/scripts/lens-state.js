const LENSES = new Set(['engineering', 'product']);
const LENS_STORAGE_KEY = 'koosha-atelier-lens';
const LENS_PROMPT_KEY = 'koosha-atelier-lens-prompted';

/**
 * Read the initial lens from URL, localStorage, or default.
 * Priority: URL ?lens= > localStorage > 'engineering'.
 * First-time visitors see a prompt (tracked via LENS_PROMPT_KEY).
 */
function initialLens() {
  if (typeof window === 'undefined') return 'engineering';

  // 1. URL ?lens=
  try {
    const urlLens = new URLSearchParams(window.location.search).get('lens');
    if (LENSES.has(urlLens)) return urlLens;
  } catch {
    /* ignore */
  }

  // 2. localStorage
  try {
    const stored = localStorage.getItem(LENS_STORAGE_KEY);
    if (LENSES.has(stored)) return stored;
  } catch {
    /* ignore */
  }

  // 3. Default
  return 'engineering';
}

export function createLensState(initial) {
  let current = LENSES.has(initial) ? initial : initialLens();
  const subscribers = new Set();

  function persist(value) {
    try {
      localStorage.setItem(LENS_STORAGE_KEY, value);
    } catch {
      /* ignore */
    }
  }

  if (LENSES.has(initial)) persist(current);

  return {
    get() {
      return current;
    },

    set(next) {
      if (!LENSES.has(next)) return false;
      if (next === current) return true;

      current = next;
      persist(next);

      for (const subscriber of subscribers) subscriber(current);
      return true;
    },

    subscribe(subscriber) {
      subscribers.add(subscriber);
      return () => subscribers.delete(subscriber);
    },

    /**
     * Returns true if this is a first-time visitor (no lens prompt seen yet).
     * Marks as prompted after call.
     */
    isFirstVisit() {
      try {
        return !localStorage.getItem(LENS_PROMPT_KEY);
      } catch {
        return false;
      }
    },

    markPrompted() {
      try {
        localStorage.setItem(LENS_PROMPT_KEY, '1');
      } catch {
        /* ignore */
      }
    },
  };
}
