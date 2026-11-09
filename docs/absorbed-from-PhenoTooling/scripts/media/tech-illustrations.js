/**
 * Inline SVG technical illustrations for case-study pages.
 *
 * Each illustration is a function that returns an SVG string.
 * Use getIllustration(name) to retrieve by name, or call initTechIllustrations()
 * to auto-replace all .tech-illustration[data-name] elements in the DOM.
 *
 * Colors: teal #7EBAB5, graphite #353A40, muted #555a52
 * Font: JetBrains Mono (via var(--font-meta))
 * All illustrations use viewBox 200x150, stroke-based for technical feel.
 */

const TEAL = '#7EBAB5';
const GRAPHITE = '#353A40';
const MUTED = '#555a52';
const FONT = "'JetBrains Mono', var(--font-meta), monospace";

/* ------------------------------------------------------------------ */
/*  1. Network Topology                                                */
/* ------------------------------------------------------------------ */

function networkTopology() {
  // Hierarchical layout: 1 root, 2 mid, 3-4 leaf nodes
  const nodes = [
    { id: 'root',   x: 100, y: 18,  r: 8,  label: 'Core' },
    { id: 'mid-l',  x: 52,  y: 58,  r: 7,  label: 'Edge-A' },
    { id: 'mid-r',  x: 148, y: 58,  r: 7,  label: 'Edge-B' },
    { id: 'leaf-1', x: 22,  y: 100, r: 6,  label: 'N1' },
    { id: 'leaf-2', x: 58,  y: 100, r: 6,  label: 'N2' },
    { id: 'leaf-3', x: 130, y: 100, r: 6,  label: 'N3' },
    { id: 'leaf-4', x: 172, y: 100, r: 6,  label: 'N4' },
  ];
  const edges = [
    ['root', 'mid-l'],
    ['root', 'mid-r'],
    ['mid-l', 'leaf-1'],
    ['mid-l', 'leaf-2'],
    ['mid-r', 'leaf-3'],
    ['mid-r', 'leaf-4'],
  ];
  const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]));

  const edgeStr = edges.map(([a, b]) => {
    const na = nodeMap[a], nb = nodeMap[b];
    return `<line x1="${na.x}" y1="${na.y}" x2="${nb.x}" y2="${nb.y}" stroke="${MUTED}" stroke-width="1.2" />`;
  }).join('\n    ');

  const nodeStr = nodes.map(n => `
    <circle cx="${n.x}" cy="${n.y}" r="${n.r}" fill="none" stroke="${TEAL}" stroke-width="1.5" />
    <text x="${n.x}" y="${n.y + n.r + 12}" text-anchor="middle" fill="${GRAPHITE}" font-family="${FONT}" font-size="7">${n.label}</text>`).join('\n    ');

  return `<svg viewBox="0 0 200 130" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="tech-net-topo-title">
  <title id="tech-net-topo-title">Network topology diagram</title>
  <defs>
    <style>text { font-family: ${FONT}; }</style>
  </defs>
  <g>${edgeStr}</g>
  <g>${nodeStr}</g>
</svg>`;
}

/* ------------------------------------------------------------------ */
/*  2. API Gateway                                                     */
/* ------------------------------------------------------------------ */

function apiGateway() {
  // Request → Gateway → Router → Service flow
  const boxes = [
    { x: 4,   y: 50, w: 36, h: 28, label: 'Request',  accent: false },
    { x: 56,  y: 50, w: 36, h: 28, label: 'Gateway',  accent: true },
    { x: 108, y: 50, w: 36, h: 28, label: 'Router',   accent: false },
    { x: 160, y: 50, w: 36, h: 28, label: 'Service',  accent: false },
  ];

  // Arrow lines between boxes
  const arrows = [
    { x1: 40, y1: 64, x2: 56, y2: 64 },
    { x1: 92, y1: 64, x2: 108, y2: 64 },
    { x1: 144, y1: 64, x2: 160, y2: 64 },
  ];

  const boxStr = boxes.map(b => {
    const stroke = b.accent ? TEAL : GRAPHITE;
    const sw = b.accent ? 2 : 1.2;
    return `<rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" rx="3" fill="none" stroke="${stroke}" stroke-width="${sw}" />
    <text x="${b.x + b.w / 2}" y="${b.y + b.h / 2 + 3}" text-anchor="middle" fill="${GRAPHITE}" font-size="7">${b.label}</text>`;
  }).join('\n    ');

  const arrowStr = arrows.map(a =>
    `<line x1="${a.x1}" y1="${a.y1}" x2="${a.x2}" y2="${a.y2}" stroke="${MUTED}" stroke-width="1.2" marker-end="url(#tech-ag-arrow)" />`
  ).join('\n    ');

  // Branch arrows from Router down to two sub-services
  const branchY = 78;
  const branchStr = `
    <line x1="126" y1="${branchY}" x2="126" y2="${branchY + 16}" stroke="${MUTED}" stroke-width="1" stroke-dasharray="3 2" />
    <line x1="126" y1="${branchY + 16}" x2="112" y2="${branchY + 16}" stroke="${MUTED}" stroke-width="1" stroke-dasharray="3 2" />
    <line x1="126" y1="${branchY + 16}" x2="140" y2="${branchY + 16}" stroke="${MUTED}" stroke-width="1" stroke-dasharray="3 2" />
    <line x1="112" y1="${branchY + 16}" x2="112" y2="${branchY + 24}" stroke="${MUTED}" stroke-width="1" stroke-dasharray="3 2" />
    <line x1="140" y1="${branchY + 16}" x2="140" y2="${branchY + 24}" stroke="${MUTED}" stroke-width="1" stroke-dasharray="3 2" />
    <text x="112" y="${branchY + 34}" text-anchor="middle" fill="${MUTED}" font-size="5.5">Svc-A</text>
    <text x="140" y="${branchY + 34}" text-anchor="middle" fill="${MUTED}" font-size="5.5">Svc-B</text>`;

  return `<svg viewBox="0 0 200 120" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="tech-api-gw-title">
  <title id="tech-api-gw-title">API gateway flow diagram</title>
  <defs>
    <marker id="tech-ag-arrow" viewBox="0 0 8 8" refX="8" refY="4" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
      <path d="M0 0 L8 4 L0 8 Z" fill="${MUTED}" />
    </marker>
    <style>text { font-family: ${FONT}; }</style>
  </defs>
  <g>${arrowStr}</g>
  <g>${boxStr}</g>
  <g>${branchStr}</g>
</svg>`;
}

/* ------------------------------------------------------------------ */
/*  3. Agent Pipeline                                                  */
/* ------------------------------------------------------------------ */

function agentPipeline() {
  // Input → Process → Output with parallel paths and gear icon
  const boxes = [
    { x: 8,   y: 48, w: 34, h: 24, label: 'Input' },
    { x: 84,  y: 48, w: 32, h: 24, label: 'Process' },
    { x: 158, y: 48, w: 34, h: 24, label: 'Output' },
  ];

  // Parallel paths above and below center
  const parallelPaths = [
    // Top path
    `<path d="M42 60 Q63 30, 84 60" fill="none" stroke="${MUTED}" stroke-width="1" stroke-dasharray="3 2" />`,
    `<path d="M116 60 Q137 30, 158 60" fill="none" stroke="${MUTED}" stroke-width="1" stroke-dasharray="3 2" />`,
    // Bottom path
    `<path d="M42 60 Q63 90, 84 60" fill="none" stroke="${MUTED}" stroke-width="1" stroke-dasharray="3 2" />`,
    `<path d="M116 60 Q137 90, 158 60" fill="none" stroke="${MUTED}" stroke-width="1" stroke-dasharray="3 2" />`,
  ];

  // Main horizontal arrows
  const mainArrows = `
    <line x1="42" y1="60" x2="84" y2="60" stroke="${GRAPHITE}" stroke-width="1.5" marker-end="url(#tech-ap-arrow)" />
    <line x1="116" y1="60" x2="158" y2="60" stroke="${GRAPHITE}" stroke-width="1.5" marker-end="url(#tech-ap-arrow)" />`;

  // Gear/atom icon in center of Process box
  const gear = `
    <circle cx="100" cy="60" r="4" fill="none" stroke="${TEAL}" stroke-width="1.5" />
    <line x1="100" y1="53" x2="100" y2="56" stroke="${TEAL}" stroke-width="1.2" />
    <line x1="100" y1="64" x2="100" y2="67" stroke="${TEAL}" stroke-width="1.2" />
    <line x1="93" y1="60" x2="96" y2="60" stroke="${TEAL}" stroke-width="1.2" />
    <line x1="104" y1="60" x2="107" y2="60" stroke="${TEAL}" stroke-width="1.2" />`;

  const boxStr = boxes.map(b =>
    `<rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" rx="3" fill="none" stroke="${GRAPHITE}" stroke-width="1.2" />
    <text x="${b.x + b.w / 2}" y="${b.y + b.h / 2 + 3}" text-anchor="middle" fill="${GRAPHITE}" font-size="7">${b.label}</text>`
  ).join('\n    ');

  // Top and bottom labels for parallel paths
  const pathLabels = `
    <text x="63" y="28" text-anchor="middle" fill="${MUTED}" font-size="5">async path</text>
    <text x="137" y="28" text-anchor="middle" fill="${MUTED}" font-size="5">async path</text>`;

  return `<svg viewBox="0 0 200 120" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="tech-agent-pipe-title">
  <title id="tech-agent-pipe-title">AI agent processing pipeline</title>
  <defs>
    <marker id="tech-ap-arrow" viewBox="0 0 8 8" refX="8" refY="4" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
      <path d="M0 0 L8 4 L0 8 Z" fill="${GRAPHITE}" />
    </marker>
    <style>text { font-family: ${FONT}; }</style>
  </defs>
  <g>${mainArrows}</g>
  <g>${parallelPaths.join('\n    ')}</g>
  <g>${boxStr}</g>
  <g>${gear}</g>
  <g>${pathLabels}</g>
</svg>`;
}

/* ------------------------------------------------------------------ */
/*  4. Security Layers                                                 */
/* ------------------------------------------------------------------ */

function securityLayers() {
  // Concentric rings: Network → Auth → Data → Core
  const layers = [
    { r: 58, label: 'Network', y: 75, color: '#7EBAB5' },
    { r: 42, label: 'Auth',    y: 75, color: '#6AABA4' },
    { r: 28, label: 'Data',    y: 75, color: '#569A92' },
    { r: 14, label: 'Core',    y: 75, color: '#438A80' },
  ];

  const ringStr = layers.map(l =>
    `<circle cx="100" cy="${l.y}" r="${l.r}" fill="none" stroke="${l.color}" stroke-width="1.5" />`
  ).join('\n    ');

  // Labels positioned to the right of each ring
  const labelStr = layers.map((l, i) => {
    const lx = 100 + l.r + 6;
    const ly = l.y - 3;
    return `<text x="${lx}" y="${ly}" fill="${GRAPHITE}" font-size="6.5">${l.label}</text>`;
  }).join('\n    ');

  // Connecting tick marks from labels to rings
  const tickStr = layers.map(l => {
    const lx = 100 + l.r;
    const ly = l.y - 5;
    return `<line x1="${lx}" y1="${ly}" x2="${lx + 4}" y2="${ly}" stroke="${MUTED}" stroke-width="0.8" />`;
  }).join('\n    ');

  return `<svg viewBox="0 0 200 150" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="tech-sec-layers-title">
  <title id="tech-sec-layers-title">Concentric security layers diagram</title>
  <defs>
    <style>text { font-family: ${FONT}; }</style>
  </defs>
  <g>${ringStr}</g>
  <g>${tickStr}</g>
  <g>${labelStr}</g>
</svg>`;
}

/* ------------------------------------------------------------------ */
/*  5. Data Flow                                                       */
/* ------------------------------------------------------------------ */

function dataFlow() {
  // System A ↔ Queue ↔ System B
  const sysA = { x: 8,  y: 48, w: 44, h: 28, label: 'System A' };
  const sysB = { x: 148, y: 48, w: 44, h: 28, label: 'System B' };
  const queue = { x: 84, y: 44, w: 32, h: 36, label: 'Queue' };

  const boxStr = [
    sysA, sysB,
  ].map(b =>
    `<rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" rx="3" fill="none" stroke="${GRAPHITE}" stroke-width="1.2" />
    <text x="${b.x + b.w / 2}" y="${b.y + b.h / 2 + 3}" text-anchor="middle" fill="${GRAPHITE}" font-size="7">${b.label}</text>`
  ).join('\n    ');

  const queueStr = `
    <rect x="${queue.x}" y="${queue.y}" width="${queue.w}" height="${queue.h}" rx="3" fill="none" stroke="${TEAL}" stroke-width="1.5" />
    <text x="${queue.x + queue.w / 2}" y="${queue.y + queue.h / 2 - 4}" text-anchor="middle" fill="${TEAL}" font-size="6.5">${queue.label}</text>
    <line x1="${queue.x + 6}" y1="${queue.y + queue.h / 2 + 4}" x2="${queue.x + queue.w - 6}" y2="${queue.y + queue.h / 2 + 4}" stroke="${MUTED}" stroke-width="0.8" />
    <line x1="${queue.x + 10}" y1="${queue.y + queue.h / 2 + 8}" x2="${queue.x + queue.w - 10}" y2="${queue.y + queue.h / 2 + 8}" stroke="${MUTED}" stroke-width="0.6" />`;

  // Bidirectional arrows
  const arrowStr = `
    <!-- A → Queue (top) -->
    <line x1="52" y1="56" x2="84" y2="56" stroke="${GRAPHITE}" stroke-width="1.2" marker-end="url(#tech-df-rarrow)" />
    <!-- Queue → A (bottom) -->
    <line x1="84" y1="74" x2="52" y2="74" stroke="${MUTED}" stroke-width="1.2" marker-end="url(#tech-df-larrow)" />
    <!-- Queue → B (top) -->
    <line x1="116" y1="56" x2="148" y2="56" stroke="${GRAPHITE}" stroke-width="1.2" marker-end="url(#tech-df-rarrow)" />
    <!-- B → Queue (bottom) -->
    <line x1="148" y1="74" x2="116" y2="74" stroke="${MUTED}" stroke-width="1.2" marker-end="url(#tech-df-larrow)" />`;

  // Flow labels
  const labelStr = `
    <text x="68" y="52" text-anchor="middle" fill="${MUTED}" font-size="5">push</text>
    <text x="68" y="82" text-anchor="middle" fill="${MUTED}" font-size="5">poll</text>
    <text x="132" y="52" text-anchor="middle" fill="${MUTED}" font-size="5">push</text>
    <text x="132" y="82" text-anchor="middle" fill="${MUTED}" font-size="5">poll</text>`;

  return `<svg viewBox="0 0 200 120" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="tech-data-flow-title">
  <title id="tech-data-flow-title">Bidirectional data flow diagram</title>
  <defs>
    <marker id="tech-df-rarrow" viewBox="0 0 8 8" refX="8" refY="4" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
      <path d="M0 0 L8 4 L0 8 Z" fill="${GRAPHITE}" />
    </marker>
    <marker id="tech-df-larrow" viewBox="0 0 8 8" refX="0" refY="4" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
      <path d="M8 0 L0 4 L8 8 Z" fill="${MUTED}" />
    </marker>
    <style>text { font-family: ${FONT}; }</style>
  </defs>
  <g>${arrowStr}</g>
  <g>${boxStr}</g>
  <g>${queueStr}</g>
  <g>${labelStr}</g>
</svg>`;
}

/* ------------------------------------------------------------------ */
/*  Registry                                                           */
/* ------------------------------------------------------------------ */

const ILLUSTRATIONS = {
  networkTopology,
  apiGateway,
  agentPipeline,
  securityLayers,
  dataFlow,
};

/**
 * Returns the SVG string for the named illustration.
 * @param {string} name — one of: networkTopology, apiGateway, agentPipeline, securityLayers, dataFlow
 * @returns {string|null} SVG string or null if name is unknown
 */
export function getIllustration(name) {
  const fn = ILLUSTRATIONS[name];
  return fn ? fn() : null;
}

/**
 * Find all .tech-illustration[data-name] elements in the document and
 * replace their innerHTML with the corresponding SVG string.
 * @param {Document} [doc=document]
 */
export function initTechIllustrations(doc = document) {
  const elements = doc.querySelectorAll('.tech-illustration[data-name]');
  for (const el of elements) {
    const name = el.getAttribute('data-name');
    const svg = getIllustration(name);
    if (svg) {
      el.innerHTML = svg;
    }
  }
}
