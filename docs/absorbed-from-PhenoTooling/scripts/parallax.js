/**
 * Parallax Depth Layer System
 *
 * Elements with `data-parallax` move at different scroll speeds:
 *   data-parallax="0.3"  — 30% of scroll speed (background)
 *   data-parallax="0.7"  — 70% (mid-ground)
 *   data-parallax="1.2"  — 120% (foreground, subtle)
 *
 * Optional attributes:
 *   data-parallax-offset  — initial Y offset in px (default 0)
 *   data-parallax-clamp   — max travel in px (default: viewport height)
 *
 * Exports: initParallax(), refreshParallax()
 */

const REDUCED_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)');

let ticking = false;
let elements = [];
let lastScrollY = 0;

/**
 * Scan the DOM for parallax elements and cache their metadata.
 */
function scanElements() {
  const raw = document.querySelectorAll('[data-parallax]');
  elements = Array.from(raw).map((el) => ({
    el,
    speed: parseFloat(el.getAttribute('data-parallax')) || 0,
    offset: parseFloat(el.getAttribute('data-parallax-offset')) || 0,
    clamp:
      parseFloat(el.getAttribute('data-parallax-clamp')) ||
      window.innerHeight,
    lastApplied: null,
  }));

  // Apply will-change to layers
  elements.forEach(({ el }) => {
    el.classList.add('parallax-layer');
    el.style.willChange = 'transform';
  });
}

/**
 * Check whether an element is within the viewport + margin.
 */
function isInViewport(rect, margin) {
  return (
    rect.bottom >= -margin &&
    rect.top <= window.innerHeight + margin
  );
}

/**
 * Clamp a value between -max and +max.
 */
function clampValue(value, max) {
  return Math.max(-max, Math.min(max, value));
}

/**
 * Apply parallax transforms for all active elements.
 */
function applyParallax() {
  const scrollY = window.scrollY;

  for (const item of elements) {
    const { el, speed, offset, clamp } = item;

    // Skip elements not in viewport (+ 200px margin)
    const rect = el.getBoundingClientRect();
    if (!isInViewport(rect, 200)) {
      continue;
    }

    // Calculate displacement: scroll distance * speed factor + offset
    let translateY = (scrollY * speed) + offset;

    // Clamp to prevent elements going off-screen
    translateY = clampValue(translateY, clamp);

    // Skip no-op transforms
    if (translateY === item.lastApplied) {
      continue;
    }

    el.style.transform = `translateY(${translateY}px)`;
    item.lastApplied = translateY;
  }

  ticking = false;
}

/**
 * Scroll handler — batch with requestAnimationFrame.
 */
function onScroll() {
  lastScrollY = window.scrollY;
  if (!ticking) {
    ticking = true;
    requestAnimationFrame(applyParallax);
  }
}

/**
 * Handle reduced-motion preference changes.
 */
function onMotionPreferenceChange() {
  if (REDUCED_MOTION.matches) {
    disableParallax();
  } else {
    enableParallax();
  }
}

function disableParallax() {
  window.removeEventListener('scroll', onScroll, { passive: true });
  elements.forEach(({ el }) => {
    el.style.transform = 'none';
    el.style.willChange = 'auto';
  });
}

function enableParallax() {
  scanElements();
  window.addEventListener('scroll', onScroll, { passive: true });
  applyParallax();
}

/**
 * Initialize the parallax system.
 * Call once on page load or after initial DOM render.
 */
export function initParallax() {
  if (REDUCED_MOTION.matches) {
    // Still scan so elements get the .parallax-layer class,
    // but don't apply transforms.
    scanElements();
    elements.forEach(({ el }) => {
      el.style.transform = 'none';
    });
    return;
  }

  scanElements();
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener(
    'resize',
    () => {
      scanElements();
      applyParallax();
    },
    { passive: true }
  );

  REDUCED_MOTION.addEventListener(
    'change',
    onMotionPreferenceChange
  );

  // Initial pass
  applyParallax();
}

/**
 * Re-scan the DOM for parallax elements.
 * Call after SPA route changes or dynamic content insertion.
 */
export function refreshParallax() {
  // Reset transforms on old elements
  elements.forEach(({ el }) => {
    el.style.transform = '';
    el.style.willChange = 'auto';
  });

  scanElements();

  if (REDUCED_MOTION.matches) {
    elements.forEach(({ el }) => {
      el.style.transform = 'none';
    });
    return;
  }

  applyParallax();
}
