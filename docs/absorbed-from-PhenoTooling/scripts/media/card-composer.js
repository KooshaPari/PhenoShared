/**
 * Generative card image composer for projects missing real screenshots.
 *
 * Produces unique Canvas-based abstract visuals seeded from project metadata.
 * Cards are visually distinct by technology stack and project category:
 *   - Technology-to-color mapping (Rust=orange, Go=cyan, TypeScript=blue, etc.)
 *   - Category-specific icons (API router, neural nodes, terminal, gears, etc.)
 *   - Tech stack badge strip
 *   - Project title watermark and label
 *
 * Output is a data URL suitable for background-image or img src.
 * Only generates for projects without a real image in the manifest.
 */

import { drawCategoryIcon, roundRect, hexToRgba } from './card-icons.js';

const CARD_WIDTH = 800;
const CARD_HEIGHT = 450;

/* ─── Design tokens ─── */

const COLORS = {
  teal: '#7EBAB5',
  olive: '#737c4c',
  arch: '#3f8795',
  graphite950: '#171a18',
  graphite900: '#20231f',
  white: '#ffffff',
};

/* ─── Technology-to-color mapping ─── */

const TECH_COLORS = {
  Rust:          '#e8734a',
  Go:            '#00add8',
  TypeScript:    '#3178c6',
  JavaScript:    '#f7df1e',
  Python:        '#3776ab',
  Swift:         '#f05138',
  Kotlin:        '#7f52ff',
  MLX:           '#5c6bc0',
  'Apple Silicon':'#a2aaad',
  Routing:       '#7EBAB5',
  Observability: '#9c7cdb',
  FUSE:          '#e6a817',
  Linux:         '#3d8c40',
  'OpenAPI':     '#6ba539',
  MCP:           '#e07c4f',
  'Provider integration': '#00add8',
  Reliability:   '#d94f4f',
  Algorithms:    '#00bcd4',
  WebSockets:    '#ff9800',
  'Cellular automata': '#7c4dff',
  AWS:           '#ff9900',
  Deployment:    '#4caf50',
  Traceability:  '#e8734a',
  Audit:         '#d94f4f',
  'Product design':'#9c7cdb',
  Manufacturing: '#78909c',
  GTM:           '#4caf50',
  'Product operations':'#9c7cdb',
  'Supplier coordination':'#78909c',
  Fulfillment:   '#78909c',
  Design:        '#e91e63',
};

const ACCENT_FALLBACK = [COLORS.teal, COLORS.olive, COLORS.arch];

/* ─── Projects that have real card images — skip these ─── */

const PROJECTS_WITH_IMAGES = new Set([
  'netweave', 'witf', 'gmk-arch', 'dss-cipher',
  'substrate', 'phenotype-omlx', 'omniroute', 'sharecli',
]);

/* ─── Seeded PRNG (mulberry32) ─── */

function mulberry32(seed) {
  let s = seed | 0;
  return function random() {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashString(str) {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

function pick(rng, arr) {
  return arr[Math.floor(rng() * arr.length)];
}

/* ─── Resolve accent colors from tech list ─── */

function resolveAccentColors(technologies) {
  if (!technologies?.length) return ACCENT_FALLBACK;
  const mapped = technologies.map((t) => TECH_COLORS[t]).filter(Boolean);
  return mapped.length >= 2 ? mapped : [...mapped, ...ACCENT_FALLBACK].slice(0, 3);
}

/* ─── Background ─── */

function drawBackground(ctx, primaryAccent) {
  const grad = ctx.createLinearGradient(0, 0, 0, CARD_HEIGHT);
  grad.addColorStop(0, COLORS.graphite950);
  grad.addColorStop(1, COLORS.graphite900);
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, CARD_WIDTH, CARD_HEIGHT);

  const rad = ctx.createRadialGradient(
    CARD_WIDTH * 0.72, CARD_HEIGHT * 0.28, 0,
    CARD_WIDTH * 0.72, CARD_HEIGHT * 0.28, CARD_WIDTH * 0.55,
  );
  rad.addColorStop(0, hexToRgba(primaryAccent, 0.07));
  rad.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = rad;
  ctx.fillRect(0, 0, CARD_WIDTH, CARD_HEIGHT);
}

/* ─── Geometric background shapes ─── */

function drawShapes(ctx, rng, accentColors) {
  const shapeCount = 3 + Math.floor(rng() * 3);
  const centers = [];

  for (let i = 0; i < shapeCount; i++) {
    const color = pick(rng, accentColors);
    const cx = 60 + rng() * (CARD_WIDTH - 120);
    const cy = 50 + rng() * (CARD_HEIGHT - 100);
    centers.push({ x: cx, y: cy });

    ctx.save();
    ctx.globalAlpha = 0.06 + rng() * 0.10;
    ctx.fillStyle = color;
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.2;

    const shape = rng();
    if (shape < 0.3) {
      const r = 30 + rng() * 70;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha += 0.04;
      ctx.stroke();
    } else if (shape < 0.6) {
      const w = 40 + rng() * 100;
      const h = 30 + rng() * 60;
      const rot = (rng() - 0.5) * 0.35;
      ctx.translate(cx, cy);
      ctx.rotate(rot);
      ctx.fillRect(-w / 2, -h / 2, w, h);
      ctx.strokeRect(-w / 2, -h / 2, w, h);
    } else if (shape < 0.82) {
      const len = 50 + rng() * 140;
      const angle = rng() * Math.PI * 2;
      ctx.lineWidth = 1.5 + rng() * 2;
      ctx.beginPath();
      ctx.moveTo(cx - Math.cos(angle) * len / 2, cy - Math.sin(angle) * len / 2);
      ctx.lineTo(cx + Math.cos(angle) * len / 2, cy + Math.sin(angle) * len / 2);
      ctx.stroke();
    } else {
      const r = 18 + rng() * 35;
      ctx.lineWidth = 1.5 + rng() * 2;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.restore();
  }
  return centers;
}

/* ─── Connecting lines between shapes ─── */

function drawConnections(ctx, rng, centers, accentColors) {
  if (centers.length < 2) return;
  ctx.save();

  for (let i = 0; i < centers.length; i++) {
    for (let j = i + 1; j < centers.length; j++) {
      if (i === 0 || rng() < 0.55) {
        const a = centers[i];
        const b = centers[j];
        ctx.globalAlpha = 0.05 + rng() * 0.06;
        ctx.strokeStyle = pick(rng, accentColors);
        ctx.lineWidth = 0.8;
        ctx.setLineDash([4 + rng() * 6, 6 + rng() * 8]);
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        const mx = (a.x + b.x) / 2 + (rng() - 0.5) * 70;
        const my = (a.y + b.y) / 2 + (rng() - 0.5) * 50;
        ctx.quadraticCurveTo(mx, my, b.x, b.y);
        ctx.stroke();
        ctx.globalAlpha = 0.12;
        ctx.setLineDash([]);
        ctx.fillStyle = pick(rng, accentColors);
        ctx.beginPath();
        ctx.arc(mx, my, 1.5, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }
  ctx.setLineDash([]);
  ctx.restore();
}

/* ─── Noise texture overlay ─── */

function drawNoise(ctx) {
  const imageData = ctx.getImageData(0, 0, CARD_WIDTH, CARD_HEIGHT);
  const d = imageData.data;
  for (let i = 0; i < d.length; i += 4) {
    const n = (Math.random() - 0.5) * 12;
    d[i]     = Math.min(255, Math.max(0, d[i] + n));
    d[i + 1] = Math.min(255, Math.max(0, d[i + 1] + n));
    d[i + 2] = Math.min(255, Math.max(0, d[i + 2] + n));
  }
  ctx.putImageData(imageData, 0, 0);
}

/* ─── Project title watermark (large, faint) ─── */

function drawTitleWatermark(ctx, title) {
  if (!title) return;
  ctx.save();
  ctx.globalAlpha = 0.055;
  ctx.fillStyle = COLORS.white;
  ctx.font = '700 150px "Space Grotesk", sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  const maxW = CARD_WIDTH * 0.85;
  let text = title;
  while (ctx.measureText(text).width > maxW && text.length > 3) {
    text = text.slice(0, -1);
  }
  if (text !== title) text += '...';

  ctx.fillText(text, CARD_WIDTH / 2, CARD_HEIGHT / 2 + 10);
  ctx.restore();
}

/* ─── Project title label (readable, bottom-left) ─── */

function drawTitleLabel(ctx, title, accent) {
  if (!title) return;
  ctx.save();
  ctx.globalAlpha = 0.82;
  ctx.fillStyle = COLORS.white;
  ctx.font = '600 22px "Space Grotesk", sans-serif';
  ctx.textAlign = 'left';
  ctx.textBaseline = 'bottom';
  ctx.fillText(title, 32, CARD_HEIGHT - 34);

  const tw = ctx.measureText(title).width;
  ctx.globalAlpha = 0.45;
  ctx.strokeStyle = accent;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(32, CARD_HEIGHT - 28);
  ctx.lineTo(32 + tw, CARD_HEIGHT - 28);
  ctx.stroke();
  ctx.restore();
}

/* ─── Tech stack badge strip ─── */

function drawTechBadges(ctx, technologies, accent) {
  if (!technologies?.length) return;
  ctx.save();

  const badges = technologies.slice(0, 4);
  let x = 32;
  const y = CARD_HEIGHT - 58;

  ctx.font = '600 11px "Space Grotesk", sans-serif';

  for (const tech of badges) {
    const tw = ctx.measureText(tech).width;
    const padX = 10;
    const bw = tw + padX * 2;
    const bh = 20;

    ctx.globalAlpha = 0.12;
    ctx.fillStyle = accent;
    roundRect(ctx, x, y - bh + 5, bw, bh, 4);
    ctx.fill();

    ctx.globalAlpha = 0.28;
    ctx.strokeStyle = accent;
    ctx.lineWidth = 0.8;
    ctx.stroke();

    ctx.globalAlpha = 0.85;
    ctx.fillStyle = COLORS.white;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(tech, x + padX, y - bh / 2 + 5);

    x += bw + 6;
  }
  ctx.restore();
}

/* ─── Category icon in upper-right quadrant ─── */

function drawCategoryIconOverlay(ctx, category, accent) {
  const ox = CARD_WIDTH * 0.78;
  const oy = CARD_HEIGHT * 0.30;
  ctx.save();
  ctx.translate(ox, oy);
  drawCategoryIcon(ctx, category, accent);
  ctx.restore();
}

/* ─── Full card render pipeline ─── */

function renderToDataURL(project) {
  const canvas = document.createElement('canvas');
  canvas.width = CARD_WIDTH;
  canvas.height = CARD_HEIGHT;
  const ctx = canvas.getContext('2d');

  const slug = project.slug || project.title || '';
  const seed = hashString(slug);
  const rng = mulberry32(seed);

  const techs = project.technologies || [];
  const category = project.category || '';
  const title = project.title || slug;

  const accentColors = resolveAccentColors(techs);
  const primaryAccent = accentColors[0];

  drawBackground(ctx, primaryAccent);
  const centers = drawShapes(ctx, rng, accentColors);
  drawConnections(ctx, rng, centers, accentColors);
  drawNoise(ctx);

  drawTitleWatermark(ctx, title);
  drawCategoryIconOverlay(ctx, category, primaryAccent);
  drawTechBadges(ctx, techs, primaryAccent);
  drawTitleLabel(ctx, title, primaryAccent);

  return canvas.toDataURL('image/webp', 0.85);
}

/* ─── Public API ─── */

const cache = new Map();

/**
 * Generate a unique abstract card image for a project.
 * Returns a data URL string (WebP). Results are cached per slug.
 *
 * @param {{ slug: string, title: string, technologies?: string[], category?: string }} project
 * @returns {string} data URL
 */
export function composeCardImage(project) {
  const slug = project?.slug ?? project?.id ?? '';
  if (cache.has(slug)) return cache.get(slug);

  const dataUrl = renderToDataURL(project);
  cache.set(slug, dataUrl);
  return dataUrl;
}

/**
 * Auto-apply generated card images to all `.work-catalog__featured-project`
 * elements that are missing a real image.
 *
 * @param {Array} projects - The PROJECTS array from data/projects.js
 */
export function initCardComposer(projects = []) {
  const projectMap = new Map();
  for (const p of projects) {
    projectMap.set(p.slug || p.id, p);
  }

  const cards = document.querySelectorAll('.work-catalog__featured-project');

  for (const card of cards) {
    if (card.querySelector('.work-catalog__featured-image')) continue;

    const link = card.getAttribute('href') || '';
    const slugMatch = link.match(/\/work\/(.+)$/);
    if (!slugMatch) continue;

    const slug = decodeURIComponent(slugMatch[1]);
    if (PROJECTS_WITH_IMAGES.has(slug)) continue;

    const meta = projectMap.get(slug) || {};
    const h3 = card.querySelector('h3');
    const title = meta.title || h3?.textContent || slug;

    const dataUrl = composeCardImage({
      slug,
      title,
      technologies: meta.technologies || [],
      category: meta.category || '',
    });

    const imageDiv = document.createElement('div');
    imageDiv.className = 'work-catalog__featured-image';

    const img = document.createElement('img');
    img.src = dataUrl;
    img.alt = `Generated abstract card for ${title}`;
    img.loading = 'lazy';
    img.decoding = 'async';

    imageDiv.appendChild(img);

    const statusP = card.querySelector('.work-catalog__featured-status');
    if (statusP?.nextElementSibling) {
      card.insertBefore(imageDiv, statusP.nextElementSibling);
    } else {
      card.prepend(imageDiv);
    }
  }
}
