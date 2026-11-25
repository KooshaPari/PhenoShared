/* ============================================================
 *  Magnetic Button Physics
 *  Spring-based cursor displacement for interactive elements.
 *  Damped harmonic oscillator: stiffness 150, damping 15, mass 1.
 *  Max displacement: 12px X, 8px Y.
 * ============================================================ */

const STIFFNESS = 150;
const DAMPING = 15;
const MASS = 1;
const MAX_X = 12;
const MAX_Y = 8;
const REDUCED_SCALE = 1.04;

const AUTO_SELECTORS = [
  ".atelier-nav a",
  ".home-primary-links a",
  ".lens-control button",
];

/** @type {Map<Element, import("./magnetic.js").MagneticState>} */
const instances = new Map();

/**
 * @typedef {{ x: number, y: number, vx: number, vy: number, targetX: number, targetY: number }} MagneticState
 */

/** True when the user prefers minimal motion. */
function prefersReduced() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Get element center relative to viewport. */
function center(el) {
  const r = el.getBoundingClientRect();
  return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
}

/**
 * Attach magnetic physics to an element.
 * Wraps mouseenter / mousemove / mouseleave with spring integration.
 */
function attach(el) {
  if (instances.has(el)) return;

  /** @type {MagneticState} */
  const s = { x: 0, y: 0, vx: 0, vy: 0, targetX: 0, targetY: 0 };

  const reduced = prefersReduced();

  function onEnter(e) {
    const c = center(el);
    const dx = e.clientX - c.x;
    const dy = e.clientY - c.y;

    if (reduced) {
      el.style.transform = `scale(${REDUCED_SCALE})`;
      return;
    }

    s.targetX = clamp(dx, MAX_X);
    s.targetY = clamp(dy, MAX_Y);
  }

  function onMove(e) {
    if (reduced) return;
    const c = center(el);
    const dx = e.clientX - c.x;
    const dy = e.clientY - c.y;
    s.targetX = clamp(dx, MAX_X);
    s.targetY = clamp(dy, MAX_Y);
  }

  function onLeave() {
    if (reduced) {
      el.style.transform = "";
      return;
    }
    s.targetX = 0;
    s.targetY = 0;
  }

  el.addEventListener("mouseenter", onEnter);
  el.addEventListener("mousemove", onMove);
  el.addEventListener("mouseleave", onLeave);

  instances.set(el, s);
}

/** Clamp value to [-max, max]. */
function clamp(v, max) {
  return Math.max(-max, Math.min(max, v));
}

/** Apply transform from state. */
function applyTransform(el, s) {
  if (Math.abs(s.x) < 0.01 && Math.abs(s.y) < 0.01 &&
      Math.abs(s.vx) < 0.01 && Math.abs(s.vy) < 0.01) {
    el.style.transform = "";
    return;
  }
  el.style.transform = `translate(${s.x.toFixed(2)}px, ${s.y.toFixed(2)}px)`;
}

/** Step one frame of spring physics for a single state. */
function step(s, dt) {
  // Damped harmonic oscillator: F = k*(target - pos) - c*vel
  const fx = STIFFNESS * (s.targetX - s.x) - DAMPING * s.vx;
  const fy = STIFFNESS * (s.targetY - s.y) - DAMPING * s.vy;

  s.vx += (fx / MASS) * dt;
  s.vy += (fy / MASS) * dt;
  s.x += s.vx * dt;
  s.y += s.vy * dt;
}

/** Main rAF loop — drives all attached elements. */
let rafId = 0;
let lastTime = 0;

function tick(now) {
  const dt = lastTime ? Math.min((now - lastTime) / 1000, 0.064) : 0.016;
  lastTime = now;

  for (const [el, s] of instances) {
    step(s, dt);
    applyTransform(el, s);
  }

  rafId = requestAnimationFrame(tick);
}

/**
 * Initialise magnetic physics.
 *
 * Collects all `.magnetic` elements plus the auto-selectors
 * (`.atelier-nav a`, `.home-primary-links a`, `.lens-control button`)
 * and attaches spring displacement handlers.
 *
 * When `prefers-reduced-motion: reduce` is active, displacement is
 * disabled and a subtle scale shift is applied instead.
 */
export function initMagnetic() {
  if (prefersReduced()) {
    // Reduced-motion: apply scale on hover only, no spring loop.
    const reducedSelectors = [".magnetic", ...AUTO_SELECTORS];
    const els = document.querySelectorAll(reducedSelectors.join(", "));
    for (const el of els) {
      el.addEventListener("mouseenter", () => {
        el.style.transform = `scale(${REDUCED_SCALE})`;
      });
      el.addEventListener("mouseleave", () => {
        el.style.transform = "";
      });
    }
    return;
  }

  const selectors = [".magnetic", ...AUTO_SELECTORS];
  const els = document.querySelectorAll(selectors.join(", "));
  for (const el of els) attach(el);

  if (!rafId) {
    lastTime = 0;
    rafId = requestAnimationFrame(tick);
  }
}
