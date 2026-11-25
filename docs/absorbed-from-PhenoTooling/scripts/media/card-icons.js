/**
 * Category-specific icon drawing functions for generated project cards.
 *
 * Each icon is drawn relative to the current canvas origin (0,0) within a
 * ~70x70 bounding box. The caller is responsible for translate/scale and
 * restore. Icons use the provided accent color at ~35% opacity.
 *
 * Exports: CATEGORY_ICONS map, drawCategoryIcon dispatcher.
 */

/* ─── Category-to-icon-type mapping ─── */

export const CATEGORY_ICONS = {
  'ai-infrastructure': 'router',
  'ai-ml':            'neural',
  'developer-tools':   'gears',
  'cloud':             'cloud',
  'systems':           'terminal',
  'simulation':        'graph',
  'design':            'palette',
  'physical-product':  'cube',
};

/* ─── Dispatcher ─── */

/**
 * Draw the category icon at the current origin.
 * Caller must set ctx.translate before calling, and ctx.restore after.
 *
 * @param {CanvasRenderingContext2D} ctx
 * @param {string} category
 * @param {string} accent - hex color
 */
export function drawCategoryIcon(ctx, category, accent) {
  const iconType = CATEGORY_ICONS[category] || 'gears';

  ctx.strokeStyle = accent;
  ctx.fillStyle = 'none';
  ctx.lineWidth = 2.2;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.globalAlpha = 0.35;

  switch (iconType) {
    case 'router':  drawRouterIcon(ctx, accent);  break;
    case 'neural':  drawNeuralIcon(ctx, accent);  break;
    case 'terminal':drawTerminalIcon(ctx, accent);break;
    case 'gears':   drawGearsIcon(ctx, accent);   break;
    case 'cloud':   drawCloudIcon(ctx, accent);   break;
    case 'graph':   drawGraphIcon(ctx, accent);   break;
    case 'palette': drawPaletteIcon(ctx, accent);  break;
    case 'cube':    drawCubeIcon(ctx, accent);    break;
    default:        drawGearsIcon(ctx, accent);
  }
}

/* ─── Individual icon draw functions ─── */

/** Router (API gateway): central box with four port boxes. */
function drawRouterIcon(ctx, accent) {
  roundRect(ctx, -28, -18, 56, 36, 6);
  ctx.stroke();

  // Left port
  roundRect(ctx, -52, -10, 20, 20, 4);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(-32, 0);
  ctx.lineTo(-28, 0);
  ctx.stroke();

  // Right port
  roundRect(ctx, 32, -10, 20, 20, 4);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(28, 0);
  ctx.lineTo(32, 0);
  ctx.stroke();

  // Top port
  roundRect(ctx, -10, -42, 20, 20, 4);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(0, -18);
  ctx.lineTo(0, -22);
  ctx.stroke();

  // Bottom port
  roundRect(ctx, -10, 22, 20, 20, 4);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(0, 18);
  ctx.lineTo(0, 22);
  ctx.stroke();

  // Inner dot
  ctx.fillStyle = accent;
  ctx.globalAlpha = 0.4;
  ctx.beginPath();
  ctx.arc(0, 0, 3, 0, Math.PI * 2);
  ctx.fill();
}

/** Neural (agent/AI): six-node connected graph. */
function drawNeuralIcon(ctx, accent) {
  const nodes = [
    { x: 0, y: -30 },
    { x: -26, y: -10 },
    { x: 26, y: -10 },
    { x: -16, y: 16 },
    { x: 16, y: 16 },
    { x: 0, y: 34 },
  ];

  // Connections
  ctx.globalAlpha = 0.2;
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      if (Math.abs(i - j) <= 2 || (i === 0 && j === 5)) {
        ctx.beginPath();
        ctx.moveTo(nodes[i].x, nodes[i].y);
        ctx.lineTo(nodes[j].x, nodes[j].y);
        ctx.stroke();
      }
    }
  }

  // Nodes
  ctx.globalAlpha = 0.45;
  for (const n of nodes) {
    ctx.fillStyle = accent;
    ctx.beginPath();
    ctx.arc(n.x, n.y, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  }
}

/** Terminal (CLI / systems): monitor with stand and prompt cursor. */
function drawTerminalIcon(ctx, accent) {
  // Monitor body
  roundRect(ctx, -34, -26, 68, 48, 6);
  ctx.stroke();

  // Screen area
  ctx.fillStyle = hexToRgba(accent, 0.06);
  roundRect(ctx, -28, -21, 56, 36, 3);
  ctx.fill();
  ctx.stroke();

  // Stand
  ctx.beginPath();
  ctx.moveTo(-10, 22);
  ctx.lineTo(10, 22);
  ctx.moveTo(0, 22);
  ctx.lineTo(0, 30);
  ctx.moveTo(-16, 30);
  ctx.lineTo(16, 30);
  ctx.stroke();

  // Prompt cursor
  ctx.fillStyle = accent;
  ctx.globalAlpha = 0.6;
  ctx.fillRect(-20, -12, 2, 14);
  ctx.font = '11px monospace';
  ctx.fillText('$', -14, -2);
}

/** Gears (libraries / developer-tools): two interlocking gears. */
function drawGearsIcon(ctx, accent) {
  drawGear(ctx, -14, 4, 22, 8, 8, accent);
  drawGear(ctx, 14, -4, 16, 6, 6, accent);
}

function drawGear(ctx, cx, cy, outerR, innerR, teeth, accent) {
  ctx.beginPath();
  const step = (Math.PI * 2) / teeth;
  for (let i = 0; i < teeth; i++) {
    const a1 = i * step;
    const a2 = a1 + step * 0.35;
    const a3 = a1 + step * 0.5;
    const a4 = a1 + step * 0.85;
    if (i === 0) {
      ctx.moveTo(cx + Math.cos(a1) * outerR, cy + Math.sin(a1) * outerR);
    }
    ctx.lineTo(cx + Math.cos(a2) * outerR, cy + Math.sin(a2) * outerR);
    ctx.lineTo(cx + Math.cos(a3) * innerR, cy + Math.sin(a3) * innerR);
    ctx.lineTo(cx + Math.cos(a4) * innerR, cy + Math.sin(a4) * innerR);
  }
  ctx.closePath();
  ctx.stroke();

  ctx.beginPath();
  ctx.arc(cx, cy, innerR * 0.4, 0, Math.PI * 2);
  ctx.stroke();
}

/** Cloud (cloud): cloud shape with upload arrow. */
function drawCloudIcon(ctx, accent) {
  ctx.beginPath();
  ctx.arc(-12, 6, 14, Math.PI * 0.8, Math.PI * 1.85);
  ctx.arc(8, -2, 18, Math.PI * 1.15, Math.PI * 0.15);
  ctx.arc(24, 6, 12, Math.PI * 1.4, Math.PI * 0.4);
  ctx.lineTo(-24, 18);
  ctx.lineTo(-24, 14);
  ctx.closePath();
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(0, 14);
  ctx.lineTo(0, -6);
  ctx.moveTo(-6, 0);
  ctx.lineTo(0, -6);
  ctx.lineTo(6, 0);
  ctx.stroke();
}

/** Graph (simulation): five nodes with connecting edges. */
function drawGraphIcon(ctx, accent) {
  const pts = [
    { x: -28, y: 14 },
    { x: -10, y: -18 },
    { x: 12, y: 6 },
    { x: 28, y: -14 },
    { x: 20, y: 20 },
  ];

  ctx.globalAlpha = 0.25;
  const edges = [[0, 1], [1, 2], [2, 3], [2, 4], [0, 2]];
  for (const [a, b] of edges) {
    ctx.beginPath();
    ctx.moveTo(pts[a].x, pts[a].y);
    ctx.lineTo(pts[b].x, pts[b].y);
    ctx.stroke();
  }

  ctx.globalAlpha = 0.45;
  for (const p of pts) {
    ctx.fillStyle = accent;
    ctx.beginPath();
    ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
    ctx.fill();
  }
}

/** Palette (design): colored swatches on an elliptical outline. */
function drawPaletteIcon(ctx, accent) {
  const swatches = ['#e8734a', '#3178c6', '#00add8', '#4caf50', '#e91e63'];
  const angles = [-0.6, -0.15, 0.3, 0.75, 1.2];
  const radius = 24;

  ctx.lineWidth = 1.5;
  for (let i = 0; i < swatches.length; i++) {
    ctx.fillStyle = hexToRgba(swatches[i], 0.5);
    ctx.globalAlpha = 0.4;
    ctx.beginPath();
    ctx.arc(
      Math.cos(angles[i]) * radius,
      Math.sin(angles[i]) * radius - 4,
      7, 0, Math.PI * 2,
    );
    ctx.fill();
    ctx.strokeStyle = accent;
    ctx.stroke();
  }

  ctx.globalAlpha = 0.25;
  ctx.strokeStyle = accent;
  ctx.beginPath();
  ctx.ellipse(0, 0, 34, 26, 0, 0, Math.PI * 2);
  ctx.stroke();
}

/** Cube (physical product): isometric cube wireframe. */
function drawCubeIcon(ctx, accent) {
  const s = 22;
  ctx.beginPath();
  ctx.moveTo(-s, s * 0.4);
  ctx.lineTo(0, s * 0.9);
  ctx.lineTo(s, s * 0.4);
  ctx.lineTo(s, -s * 0.4);
  ctx.lineTo(0, -s * 0.1);
  ctx.lineTo(-s, -s * 0.4);
  ctx.closePath();
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(-s, -s * 0.4);
  ctx.lineTo(0, -s * 0.9);
  ctx.lineTo(s, -s * 0.4);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(0, -s * 0.1);
  ctx.lineTo(0, s * 0.9);
  ctx.stroke();
}

/* ─── Shared helpers ─── */

/** Draw a rounded rectangle path (does not stroke/fill). */
export function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.arcTo(x + w, y, x + w, y + r, r);
  ctx.lineTo(x + w, y + h - r);
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
  ctx.lineTo(x + r, y + h);
  ctx.arcTo(x, y + h, x, y + h - r, r);
  ctx.lineTo(x, y + r);
  ctx.arcTo(x, y, x + r, y, r);
  ctx.closePath();
}

/** Convert a hex color string to rgba(). */
export function hexToRgba(hex, alpha) {
  const h = hex.replace('#', '');
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}
