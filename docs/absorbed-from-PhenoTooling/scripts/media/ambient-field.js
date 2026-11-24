/**
 * Ambient particle field — generative canvas background for the homepage hero.
 *
 * Types: dust motes (tiny dots), constellation lines (thin connections),
 * nodes (pulsing larger circles). Precision-aesthetic, not organic.
 *
 * Usage:
 *   import { initAmbientField } from '../media/ambient-field.js';
 *   initAmbientField(document.querySelector('.home-opening'));
 */

const PARTICLE_COLOR = 'rgba(126, 186, 181, 0.3)';
const LINE_COLOR     = 'rgba(126, 186, 181, 0.08)';
const NODE_COLOR     = 'rgba(126, 186, 181, 0.6)';

const DESKTOP_COUNT  = 60;
const MOBILE_COUNT   = 30;
const MIN_COUNT      = 4;

const LINE_DISTANCE  = 120;
const NODE_RADIUS    = { min: 3, max: 4 }; // half of 6-8px
const DUST_RADIUS    = 1;

const SPEED_MIN      = 0.1;
const SPEED_MAX      = 0.3;
const SINE_AMPLITUDE = 0.15;
const SINE_PERIOD    = 0.003;

const RESIZE_DEBOUNCE_MS = 200;

/**
 * Create a single particle with deterministic-ish initial state.
 */
function createParticle(width, height, index, isNode) {
  const angle = (index * 2.39996) % (2 * Math.PI); // golden angle spread
  const radius = 0.15 + ((index * 7 + 3) % 100) / 100 * 0.7; // 0.15–0.85 of bounds
  return {
    x: width * 0.5 + Math.cos(angle) * width * radius * 0.5,
    y: height * 0.5 + Math.sin(angle) * height * radius * 0.5,
    vx: SPEED_MIN + ((index * 13 + 7) % 100) / 100 * (SPEED_MAX - SPEED_MIN),
    vy: SPEED_MIN + ((index * 17 + 11) % 100) / 100 * (SPEED_MAX - SPEED_MIN),
    phase: (index * 1.7) % (2 * Math.PI),
    isNode,
    nodePulse: 0,
    nodePulseDir: 1,
  };
}

/**
 * Build the particle array based on viewport width.
 */
function buildParticles(width, height, lowEnd) {
  const isMobile = width < 768;
  const count = lowEnd ? MIN_COUNT : (isMobile ? MOBILE_COUNT : DESKTOP_COUNT);
  const particles = [];
  for (let i = 0; i < count; i++) {
    const isNode = !isMobile && i % 8 === 0 && !lowEnd;
    particles.push(createParticle(width, height, i, isNode));
  }
  return particles;
}

/**
 * Advance particle positions by one frame.
 */
function ambientStep(particles, width, height, frame) {
  for (const p of particles) {
    const sineOffset = Math.sin(frame * SINE_PERIOD + p.phase) * SINE_AMPLITUDE;
    p.x += p.vx + sineOffset;
    p.y += p.vy;

    // Wrap around edges with padding
    const pad = LINE_DISTANCE;
    if (p.x > width + pad) p.x = -pad;
    if (p.x < -pad) p.x = width + pad;
    if (p.y > height + pad) p.y = -pad;
    if (p.y < -pad) p.y = height + pad;

    // Node pulse
    if (p.isNode) {
      p.nodePulse += 0.008 * p.nodePulseDir;
      if (p.nodePulse >= 1) { p.nodePulse = 1; p.nodePulseDir = -1; }
      if (p.nodePulse <= 0) { p.nodePulse = 0; p.nodePulseDir = 1; }
    }
  }
}

/**
 * Draw one frame: lines first, then dust, then nodes on top.
 */
function draw(ctx, particles, width, height) {
  ctx.clearRect(0, 0, width, height);

  // --- Constellation lines ---
  ctx.strokeStyle = LINE_COLOR;
  ctx.lineWidth = 1;
  const dust = particles.filter(p => !p.isNode);
  for (let i = 0; i < dust.length; i++) {
    for (let j = i + 1; j < dust.length; j++) {
      const dx = dust[i].x - dust[j].x;
      const dy = dust[i].y - dust[j].y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < LINE_DISTANCE) {
        const alpha = 1 - dist / LINE_DISTANCE;
        ctx.globalAlpha = alpha * 0.5; // reinforce the 8% base
        ctx.beginPath();
        ctx.moveTo(dust[i].x, dust[i].y);
        ctx.lineTo(dust[j].x, dust[j].y);
        ctx.stroke();
      }
    }
  }
  ctx.globalAlpha = 1;

  // --- Dust motes ---
  ctx.fillStyle = PARTICLE_COLOR;
  for (const p of dust) {
    ctx.beginPath();
    ctx.arc(p.x, p.y, DUST_RADIUS, 0, 2 * Math.PI);
    ctx.fill();
  }

  // --- Nodes (pulsing) ---
  for (const p of particles) {
    if (!p.isNode) continue;
    const r = NODE_RADIUS.min + p.nodePulse * (NODE_RADIUS.max - NODE_RADIUS.min);
    ctx.globalAlpha = 0.35 + p.nodePulse * 0.25;
    ctx.fillStyle = NODE_COLOR;
    ctx.beginPath();
    ctx.arc(p.x, p.y, r, 0, 2 * Math.PI);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
}

/**
 * Draw a static field — 3 subtle dots, no animation, for reduced-motion users.
 */
function drawStatic(ctx, width, height) {
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = PARTICLE_COLOR;
  const positions = [
    { x: width * 0.25, y: height * 0.35 },
    { x: width * 0.55, y: height * 0.6 },
    { x: width * 0.78, y: height * 0.28 },
  ];
  for (const pos of positions) {
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, DUST_RADIUS, 0, 2 * Math.PI);
    ctx.fill();
  }
}

/**
 * Initialise the ambient particle field inside the given container.
 *
 * @param {HTMLElement} container — the hero section element
 */
export function initAmbientField(container) {
  if (!container || !document.createElement('canvas').getContext) return;

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const lowEnd = (navigator.hardwareConcurrency || 4) <= 4;

  const canvas = document.createElement('canvas');
  canvas.className = 'ambient-field-canvas';
  canvas.setAttribute('aria-hidden', 'true');
  canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:0;';

  // Make container the positioning context
  const prevPosition = getComputedStyle(container).position;
  if (prevPosition === 'static') {
    container.style.position = 'relative';
  }
  // Ensure existing children layer above the canvas
  container.style.isolation = 'isolate';
  container.insertBefore(canvas, container.firstChild);

  const ctx = canvas.getContext('2d');
  let width = 0;
  let height = 0;
  let particles = [];
  let frame = 0;
  let rafId = 0;
  let paused = false;

  function resize() {
    const rect = container.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = Math.round(rect.width);
    height = Math.round(rect.height);
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    particles = buildParticles(width, height, lowEnd);

    if (prefersReducedMotion) {
      drawStatic(ctx, width, height);
    }
  }

  function tick() {
    if (paused) return;
    frame++;
    if (!Array.isArray(particles) || !particles.length) {
      rafId = requestAnimationFrame(tick);
      return;
    }
    ambientStep(particles, width, height, frame);
    draw(ctx, particles, width, height);
    rafId = requestAnimationFrame(tick);
  }

  // Debounced resize
  let resizeTimer = 0;
  function onResize() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(resize, RESIZE_DEBOUNCE_MS);
  }

  // Pause when tab hidden
  function onVisibility() {
    if (document.hidden) {
      paused = true;
      cancelAnimationFrame(rafId);
    } else {
      paused = false;
      rafId = requestAnimationFrame(tick);
    }
  }

  resize();
  if (!prefersReducedMotion) {
    rafId = requestAnimationFrame(tick);
  }

  window.addEventListener('resize', onResize, { passive: true });
  document.addEventListener('visibilitychange', onVisibility);

  // Return a teardown handle in case the view unmounts
  return function destroy() {
    cancelAnimationFrame(rafId);
    clearTimeout(resizeTimer);
    window.removeEventListener('resize', onResize);
    document.removeEventListener('visibilitychange', onVisibility);
    canvas.remove();
  };
}
