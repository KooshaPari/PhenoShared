/**
 * Custom Precision Cursor System
 *
 * Crosshair dot (6px) + outer ring (32px) with smooth lerp following.
 * States: default, hover, click, text, image.
 * Trail effect on fast movement. Touch / reduced-motion safe.
 *
 * @module cursor
 */

const INTERACTIVE_SELECTOR =
  'a, button, [role="button"], input, textarea, select, .clickable, .interactive';

const IMAGE_SELECTOR =
  '.artifact, figure, .project-card img';

const TRAIL_COUNT = 3;
const LERP_SPEED = 0.15;
const LERP_REDUCED = 0.35;

/** Speed threshold (px/frame) above which trail dots appear. */
const TRAIL_SPEED_THRESHOLD = 8;

/** Whether the device supports fine pointer input. */
function hasFinePointer() {
  return matchMedia('(pointer: fine)').matches;
}

/** Whether the user prefers reduced motion. */
function prefersReducedMotion() {
  return matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Linearly interpolate between `a` and `b` by factor `t`.
 */
function lerp(a, b, t) {
  return a + (b - a) * t;
}

/**
 * Create and mount the cursor DOM elements.
 * Returns { dot, ring, trails[] }.
 */
function createDOM() {
  const dot = document.createElement('div');
  dot.className = 'cursor-dot';
  dot.setAttribute('aria-hidden', 'true');

  const ring = document.createElement('div');
  ring.className = 'cursor-ring';
  ring.setAttribute('aria-hidden', 'true');

  const trails = [];
  for (let i = 0; i < TRAIL_COUNT; i++) {
    const t = document.createElement('div');
    t.className = 'cursor-trail';
    t.setAttribute('aria-hidden', 'true');
    document.body.appendChild(t);
    trails.push({ el: t, x: 0, y: 0 });
  }

  document.body.appendChild(ring);
  document.body.appendChild(dot);

  return { dot, ring, trails };
}

/**
 * Determine cursor state from the element under the pointer.
 *
 * @param {Element} target - The deepest element under the cursor.
 * @returns {'default'|'hover'|'text'|'image'}
 */
function stateForTarget(target) {
  if (!target || !target.closest) return 'default';

  // Image containers get magnify state
  if (target.closest(IMAGE_SELECTOR)) return 'image';

  // Text inputs get I-beam
  if (
    target.matches('input:not([type="button"]):not([type="submit"]):not([type="checkbox"]):not([type="radio"])') ||
    target.matches('textarea') ||
    target.matches('[contenteditable="true"]')
  ) {
    return 'text';
  }

  // Interactive elements
  if (target.closest(INTERACTIVE_SELECTOR)) return 'hover';

  return 'default';
}

/**
 * Initialise the custom cursor system.
 * Safe to call multiple times; subsequent calls are no-ops.
 *
 * @returns {void}
 */
export function initCursor() {
  if (!hasFinePointer()) return;
  if (document.querySelector('.cursor-dot')) return; // already mounted

  const reduced = prefersReducedMotion();
  const lerpSpeed = reduced ? LERP_REDUCED : LERP_SPEED;

  const { dot, ring, trails } = createDOM();

  // ---- state ----
  let mouseX = -100;
  let mouseY = -100;
  let dotX = -100;
  let dotY = -100;
  let ringX = -100;
  let ringY = -100;
  let currentState = 'default';
  let isClicking = false;
  let raf = null;

  // ---- event handlers ----

  function onMouseMove(e) {
    mouseX = e.clientX;
    mouseY = e.clientY;
  }

  function onMouseDown() {
    isClicking = true;
    ring.classList.add('cursor-ring--click');
  }

  function onMouseUp() {
    isClicking = false;
    ring.classList.remove('cursor-ring--click');
  }

  function onMouseEnter() {
    dot.style.opacity = '1';
    ring.style.opacity = '1';
  }

  function onMouseLeave() {
    dot.style.opacity = '0';
    ring.style.opacity = '0';
  }

  function onPointerOver(e) {
    const nextState = stateForTarget(e.target);
    applyState(nextState);
  }

  function applyState(next) {
    if (next === currentState) return;

    // Remove previous state classes
    dot.classList.remove('cursor-dot--text', 'cursor-dot--image');
    ring.classList.remove('cursor-ring--hover');

    currentState = next;

    switch (next) {
      case 'hover':
        ring.classList.add('cursor-ring--hover');
        break;
      case 'text':
        dot.classList.add('cursor-dot--text');
        break;
      case 'image':
        dot.classList.add('cursor-dot--image');
        ring.classList.add('cursor-ring--hover');
        break;
      // 'default' — no extra classes
    }
  }

  // ---- animation loop ----

  function tick() {
    // Lerp dot toward mouse
    dotX = lerp(dotX, mouseX, lerpSpeed);
    dotY = lerp(dotY, mouseY, lerpSpeed);

    // Ring follows slightly behind dot for depth
    ringX = lerp(ringX, dotX, lerpSpeed * 0.85);
    ringY = lerp(ringY, dotY, lerpSpeed * 0.85);

    dot.style.transform = `translate(${dotX}px, ${dotY}px)`;
    ring.style.transform = `translate(${ringX}px, ${ringY}px)`;

    // Trail: store position history and update trail dots
    if (!reduced) {
      const speed = Math.hypot(mouseX - (trails[0]?.prevX ?? mouseX), mouseY - (trails[0]?.prevY ?? mouseY));
      trails[0].prevX = mouseX;
      trails[0].prevY = mouseY;

      for (let i = trails.length - 1; i > 0; i--) {
        trails[i].x = trails[i - 1].x;
        trails[i].y = trails[i - 1].y;
      }
      trails[0].x = dotX;
      trails[0].y = dotY;

      for (let i = 0; i < trails.length; i++) {
        const opacity = speed > TRAIL_SPEED_THRESHOLD
          ? [0.18, 0.10, 0.05][i] * Math.min(speed / 40, 1)
          : 0;
        trails[i].el.style.transform = `translate(${trails[i].x}px, ${trails[i].y}px)`;
        trails[i].el.style.opacity = String(opacity);
      }
    }

    raf = requestAnimationFrame(tick);
  }

  // ---- bind ----
  document.addEventListener('mousemove', onMouseMove, { passive: true });
  document.addEventListener('mousedown', onMouseDown, { passive: true });
  document.addEventListener('mouseup', onMouseUp, { passive: true });
  document.addEventListener('mouseenter', onMouseEnter);
  document.addEventListener('mouseleave', onMouseLeave);
  document.addEventListener('pointerover', onPointerOver, { passive: true });

  // Start animation
  raf = requestAnimationFrame(tick);

  // ---- cleanup export (for SPA route changes or teardown) ----
  // Attaches a once-listener so the module can be reinitialised after cleanup.
  window.__cursorCleanup = () => {
    cancelAnimationFrame(raf);
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mousedown', onMouseDown);
    document.removeEventListener('mouseup', onMouseUp);
    document.removeEventListener('mouseenter', onMouseEnter);
    document.removeEventListener('mouseleave', onMouseLeave);
    document.removeEventListener('pointerover', onPointerOver);
    dot.remove();
    ring.remove();
    trails.forEach((t) => t.el.remove());
  };
}
