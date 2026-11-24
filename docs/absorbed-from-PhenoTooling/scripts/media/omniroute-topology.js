import { el } from '../components/dom.js';

// Conceptual overview, grounded in OmniRoute ba597b631d22d85e56db6982f24b7d1ebe238df9:
// src/sse/handlers/chat.ts:1106-1137 (combo -> single target)
// src/sse/services/auth.ts:1458-1508 (connection/model eligibility)
// src/sse/handlers/chatHelpers.ts:382-390 (provider breaker gate)
// open-sse/handlers/chatCore.ts:2494,3168 (translation / executor)
// open-sse/services/combo/executeTargetAttempt.ts:356,662 (dispatch / response)
// open-sse/services/combo/comboAttemptLoop.ts:453-503 (bounded conditional retry)
const SUMMARY = 'Conceptual routing overview, not a universal execution trace or live telemetry. Direct-model and combo strategies differ; fallback depends on eligibility, error classification and configured limits.';
const STEPS = [
  'Request -> Target selection: resolve the requested model or configured combo.',
  'Target selection -> Provider execution: select an eligible target and connection; provider breaker, connection cooldown and model lockout have distinct scopes.',
  'Provider execution -> Response: a successful attempt returns a response.',
  'Provider execution -> Failure state: classify an unsuccessful attempt; not every error changes every failure mechanism.',
  'Failure state -> Target selection: eligible fallback or bounded retry only when policy permits.',
  'Failure state -> Response: stop or exhausted attempts return an error; fallback is not guaranteed.',
];

function svgEl(tag, attributes = {}, ...children) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  for (const child of children) node.append(typeof child === 'string' ? document.createTextNode(child) : child);
  return node;
}

export function renderOmniRouteTopology(lens = 'engineering') {
  const prefix = `omniroute-topology-${lens}`;
  const nodes = [
    ['request', 'Request', 24, 24],
    ['selection', 'Target selection', 24, 120],
    ['execution', 'Provider execution', 24, 216],
    ['response', 'Response', 24, 368],
    ['failure', 'Failure state', 330, 216],
  ];
  const edges = [
    ['request-selection', 'M134 80 V120', false],
    ['selection-execution', 'M134 176 V216', false],
    ['execution-response', 'M134 272 V368', false],
    ['execution-failure', 'M244 244 H330', true],
    ['failure-selection', 'M440 216 V148 H244', true],
    ['failure-response', 'M440 272 V396 H244', true],
  ];
  const svg = svgEl('svg', {
    class: 'case-svg-diagram omniroute-topology__desktop', viewBox: '0 0 580 448', role: 'img',
    'data-topology': 'omniroute', 'aria-labelledby': `${prefix}-title ${prefix}-desc`,
  },
  svgEl('title', { id: `${prefix}-title` }, 'OmniRoute conditional routing overview'),
  svgEl('desc', { id: `${prefix}-desc` }, `${SUMMARY} ${STEPS.join(' ')}`),
  svgEl('defs', {}, svgEl('marker', {
    id: `${prefix}-arrow`, viewBox: '0 0 10 10', refX: 10, refY: 5,
    markerWidth: 6, markerHeight: 6, orient: 'auto-start-reverse',
  }, svgEl('path', { d: 'M0 0 L10 5 L0 10 Z', fill: 'var(--arch-500)' }))),
  ...edges.map(([id, d, conditional]) => svgEl('path', {
    'data-edge': id, d, fill: 'none', class: 'case-svg-diagram__edge',
    'marker-end': `url(#${prefix}-arrow)`, ...(conditional ? { 'stroke-dasharray': '6 5' } : {}),
  })),
  ...nodes.map(([id, label, x, y]) => svgEl('g', {
    'data-node': id, class: 'case-svg-diagram__node', transform: `translate(${x} ${y})`,
  }, svgEl('rect', { width: 220, height: 56, rx: 3 }), svgEl('text', { x: 14, y: 33 }, label))),
  );
  const mobile = el('div', { class: 'omniroute-topology__mobile' },
    el('ol', {}, ...nodes.slice(0, 4).map(([id, label]) =>
      el('li', { 'data-mobile-node': id }, label))),
    el('div', { 'data-mobile-node': 'failure' },
      el('strong', {}, 'Failure state'),
      el('p', {}, 'Execution failure: eligible fallback or bounded retry returns to selection. On stop or exhausted attempts, return an error response.'),
    ),
  );
  const plate = el('div', { class: 'omniroute-topology__plate' },
    el('div', { class: 'omniroute-topology__plate-header' },
      el('span', {}, 'OmniRoute / routing plate'),
      el('span', {}, 'Conceptual model'),
    ),
    svg, mobile,
    el('ul', { class: 'omniroute-topology__legend', 'aria-label': 'Routing path legend' },
      el('li', { class: 'omniroute-topology__legend-main' }, 'Request / response path'),
      el('li', { class: 'omniroute-topology__legend-conditional' }, 'Conditional failure path'),
    ),
  );
  return el('figure', { class: 'case-diagram-figure omniroute-topology' }, plate,
    el('figcaption', {}, 'OmniRoute / upstream routing overview. Failure paths are conditional; dashed in the diagram.'),
    el('p', { class: 'omniroute-topology__qualification' }, SUMMARY),
    el('details', { class: 'omniroute-topology__reader', 'data-topology-reader': 'omniroute' },
      el('summary', {}, 'Read routing paths'),
      el('ol', {}, ...STEPS.map(step => el('li', {}, step))),
    ),
  );
}
