const TEAL = '#7EBAB5';
const SHAPE_COUNT = 18;
const SPEED = 0.05;

/**
 * Generate an array of drifting geometric shapes.
 */
function createShapes(width, height) {
  const types = ['triangle', 'circle', 'line'];
  const shapes = [];

  for (let i = 0; i < SHAPE_COUNT; i++) {
    shapes.push({
      x: Math.random() * width,
      y: Math.random() * height,
      type: types[i % 3],
      size: 20 + Math.random() * 80,
      rotation: Math.random() * Math.PI * 2,
      rotationSpeed: (Math.random() - 0.5) * 0.002,
      vx: (Math.random() - 0.5) * SPEED * 2,
      vy: (Math.random() - 0.5) * SPEED * 2,
      opacity: 0.1 + Math.random() * 0.1,
    });
  }

  return shapes;
}

/**
 * Draw a single geometric shape on the canvas context.
 */
function drawShape(ctx, shape) {
  ctx.save();
  ctx.translate(shape.x, shape.y);
  ctx.rotate(shape.rotation);
  ctx.globalAlpha = shape.opacity;
  ctx.strokeStyle = TEAL;
  ctx.lineWidth = 1;

  const half = shape.size / 2;

  if (shape.type === 'triangle') {
    ctx.beginPath();
    ctx.moveTo(0, -half);
    ctx.lineTo(-half, half);
    ctx.lineTo(half, half);
    ctx.closePath();
    ctx.stroke();
  } else if (shape.type === 'circle') {
    ctx.beginPath();
    ctx.arc(0, 0, half, 0, Math.PI * 2);
    ctx.stroke();
  } else {
    ctx.beginPath();
    ctx.moveTo(-half, 0);
    ctx.lineTo(half, 0);
    ctx.stroke();
  }

  ctx.restore();
}

/**
 * Frame loop: drift, rotate, and redraw all shapes.
 * Wraps shapes across viewport edges.
 */
function tick(ctx, shapes, width, height) {
  ctx.clearRect(0, 0, width, height);

  for (const shape of shapes) {
    shape.x += shape.vx;
    shape.y += shape.vy;
    shape.rotation += shape.rotationSpeed;

    if (shape.x < -shape.size) shape.x = width + shape.size;
    if (shape.x > width + shape.size) shape.x = -shape.size;
    if (shape.y < -shape.size) shape.y = height + shape.size;
    if (shape.y > height + shape.size) shape.y = -shape.size;

    drawShape(ctx, shape);
  }

  requestAnimationFrame(() => tick(ctx, shapes, width, height));
}

/**
 * Initialise the generative-art canvas.
 * Call after the rendered HTML is in the DOM.
 *
 * Respects prefers-reduced-motion: renders a static composition
 * with no animation when the user prefers reduced motion.
 */
export function initCanvas() {
  const canvas = document.getElementById('not-found-canvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const dpr = window.devicePixelRatio || 1;
  const width = window.innerWidth;
  const height = window.innerHeight;

  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  ctx.scale(dpr, dpr);

  const shapes = createShapes(width, height);

  // Draw the initial static frame for every shape
  for (const shape of shapes) {
    drawShape(ctx, shape);
  }

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (!reducedMotion) {
    requestAnimationFrame(() => tick(ctx, shapes, width, height));
  }
}

/**
 * Return the full 404 page markup.
 * Include a <style> block scoped to the not-found view.
 */
export function render() {
  return `
<style>
  .not-found {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    overflow: hidden;
  }

  .not-found-canvas {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
  }

  .not-found-content {
    position: relative;
    z-index: 1;
    text-align: center;
    padding: 2rem;
  }

  .not-found-404 {
    font-family: var(--font-display), 'Space Grotesk', sans-serif;
    font-size: clamp(6rem, 10vw, 10rem);
    font-weight: 700;
    line-height: 1;
    color: var(--ink, #171a18);
    opacity: 0.08;
    margin: 0;
    user-select: none;
  }

  .not-found-subtitle {
    font-family: var(--font-body), 'Inter', sans-serif;
    font-size: clamp(1rem, 2vw, 1.25rem);
    font-weight: 400;
    color: var(--ink, #171a18);
    opacity: 0.6;
    margin: 1rem 0 2.5rem;
  }

  .not-found-home {
    display: inline-block;
    font-family: var(--font-body), 'Inter', sans-serif;
    font-size: 0.875rem;
    font-weight: 500;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    text-decoration: none;
    color: var(--ink, #171a18);
    border: 1px solid color-mix(in srgb, var(--seed-teal, ${TEAL}) 40%, transparent);
    padding: 0.75rem 2rem;
    border-radius: 2px;
    transition: background 0.3s cubic-bezier(0.16, 1, 0.3, 1),
                border-color 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .not-found-home:hover {
    background: color-mix(in srgb, var(--seed-teal, ${TEAL}) 10%, transparent);
    border-color: var(--seed-teal, ${TEAL});
  }
</style>

<section class="view active portfolio-view not-found">
  <canvas id="not-found-canvas" class="not-found-canvas"></canvas>
  <div class="not-found-content">
    <p class="not-found-404">404</p>
    <h1 class="not-found-subtitle">Page not found</h1>
    <a href="/" class="not-found-home magnetic">Return home</a>
  </div>
</section>`;
}
