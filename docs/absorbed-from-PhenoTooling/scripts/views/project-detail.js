import { PROJECTS } from '../../data/projects.js';
import { el } from '../components/dom.js';
import { metricAnnotation, evidenceLabel, publicEvidenceSummary } from '../components/evidence.js';
import { diagramFromCaseStudy, renderDiagram } from '../media/diagrams.js';
import { renderNetWeaveWorkbench } from '../media/netweave-workbench.js';
import { renderShareCliWorkbench } from '../media/sharecli-workbench.js';
import { renderShareCliRecordings } from '../media/sharecli-recording.js';
import { renderSubstratePlate } from '../media/systems-plate.js';
import { render as renderNotFound } from './not-found.js';

const COMPACT_SECTIONS = {
  byteport: [
    ['Context', 'Declarative Go/AWS deployment tooling with a deliberately explicit boundary between current behavior and planned delivery.'],
    ['Current boundary', 'The record does not claim Firecracker, microVM, or live public deployment delivery without repository evidence.'],
    ['Why it matters', 'The useful contribution is making deployment intent reviewable before infrastructure is provisioned.'],
  ],
  tracera: [
    ['Context', 'Traceability and audit infrastructure for software and agent workflows.'],
    ['Focus', 'The project organizes provenance and operational evidence without claiming unsupported adoption or deployment scale.'],
    ['Current boundary', 'Repository status is the source of truth; production rollout claims are intentionally omitted.'],
  ],
  'dss-cipher': [
    ['Context', 'Historical keyset concept preserved as a compact visual/product entry.'],
    ['Evidence', 'Renders, kitting, collaborations, and community-interest links are retained where captured.'],
    ['Current boundary', 'Unavailable external destinations and limited outcome evidence keep this out of the full case-study tier.'],
  ],
  'cliproxyapi-plusplus': [
    ['Context', 'A forked multi-provider AI proxy focused on routing, auth, quotas, diagnostics, and operational controls.'],
    ['Upstream boundary', 'Attributed to router-for-me/CLIProxyAPI; only KooshaPari\u2019s extension scope is presented here.'],
    ['Current boundary', 'Upstream popularity is not imported as local adoption evidence.'],
  ],
  'agentapi-plusplus': [
    ['Context', 'Agent API extension work built on an upstream agent interface.'],
    ['Upstream boundary', 'Attributed to coder/agentapi; this entry describes extension scope only.'],
    ['Current boundary', 'No unsupported deployment or adoption claim is made.'],
  ],
  mcpforge: [
    ['Context', 'Historical MCP tooling entry preserved for provenance and archive discoverability.'],
    ['Upstream boundary', 'Attribution to isaacphi/mcp-language-server remains visible.'],
  ],
  forgecode: [
    ['Context', 'Historical agent-tooling entry retained as an archive record.'],
    ['Upstream boundary', 'Attribution to tailcallhq/forgecode remains visible.'],
  ],
  frostify: [
    ['Context', 'Historical, unmaintained Spicetify theme fork with transparent/frosted styling.'],
    ['Evidence', 'GitHub records 3,350+ release-asset downloads; this is not a user count.'],
    ['Upstream boundary', 'Fork attribution to gwennlbh/Frostify remains explicit.'],
  ],
};

export function renderProjectDetail(root, slug, lens = 'engineering') {
  const project = PROJECTS.find(p => p.slug === slug);
  if (!project) return renderNotFound(root, slug);

  const metrics = project.metrics?.length
    ? el('div', { class: 'metric-grid' },
        project.metrics.map(([value, label, source]) =>
          el('div', { class: 'metric-card' },
            el('strong', {}, value), el('span', {}, label), el('small', {}, source))))
    : null;

  const defaultSections = project.category === 'physical-product'
    ? [
        ['Context', 'A technically complex physical product shaped by constraints, suppliers, and real-world demand.'],
        ['Decisions', 'Presented as an evidence-led product narrative; historical facts retain their qualifiers.'],
        ['Outcome', 'Commercial and launch claims are labeled in the evidence ledger rather than inflated in prose.'],
      ]
    : [
        ['Problem', 'A concrete engineering problem is framed before implementation details.'],
        ['Architecture', 'The system boundary, runtime choices, and operational constraints are kept explicit.'],
        ['Verification', 'Current status and limitations follow the reconciled GitHub evidence.'],
      ];

  const sections = project.caseStudy?.sections || COMPACT_SECTIONS[project.slug] || defaultSections;

  const overview = project.caseStudy?.overview
    ? el('div', { class: 'case-section case-overview' }, el('h2', {}, 'Overview'), el('p', {}, project.caseStudy.overview))
    : null;

  const diagram = project.caseStudy?.diagram
    ? el('div', { class: 'case-section case-diagram' }, el('h2', {}, 'Architecture'), renderDiagram(diagramFromCaseStudy(project), { title: `${project.title} architecture` }))
    : null;
  const netweaveField = project.slug === 'netweave'
    ? el('div', { class: 'case-section case-netweave-field' }, el('h2', {}, 'Traffic field'), renderNetWeaveWorkbench())
    : null;
  const shareCliWorkbench = project.slug === 'sharecli'
    ? el('div', { class: 'case-section case-sharecli-workbench' }, el('h2', {}, 'Runtime boundary'), renderShareCliWorkbench(), renderShareCliRecordings())
    : null;
  const substratePlate = project.slug === 'substrate'
    ? el('div', { class: 'case-section case-substrate-plate' }, el('h2', {}, 'Execution boundary'), renderSubstratePlate())
    : null;

  const disclosure = project.caseStudy?.disclosure
    ? el('div', { class: 'case-section case-disclosure' }, el('h2', {}, 'AI-assistance disclosure'), el('p', {}, project.caseStudy.disclosure))
    : null;

  const evidence = project.caseStudy?.evidenceRefs?.length
    ? el('div', { class: 'case-section case-evidence' }, el('h2', {}, 'Evidence status'),
        project.caseStudy.evidenceRefs.map(ref => el('p', {}, ref)))
    : null;

  // Evidence Panel (per §13 - Evidence & Provenance UX)
  const evidencePanel = (project.evidence || project.provenance || project.repo)
    ? el('div', { class: 'case-section case-evidence-panel' },
        el('h2', {}, 'Provenance & Attribution'),
        el('dl', { class: 'evidence-list' },
          project.evidence ? el('div', {}, el('dt', {}, 'Evidence source'), el('dd', {}, publicEvidenceSummary(project))) : null,
          project.provenance ? el('div', {}, el('dt', {}, 'Provenance'), el('dd', {}, project.provenance)) : null,
          project.repo ? el('div', {}, el('dt', {}, 'Repository'), el('dd', {}, el('a', { href: project.repo, target: '_blank', rel: 'noreferrer' }, project.repo))) : null,
          project.lens ? el('div', {}, el('dt', {}, 'Available in lens'), el('dd', {}, project.lens.join(', '))) : null,
        ),
      )
    : null;

  // Lens-aware annotation
  const lensAnnotation = project.presentation?.annotations?.[lens]
    ? el('div', { class: 'lens-annotation', 'data-lens': lens },
        el('h3', {}, lens === 'product' ? 'Product lens' : 'Engineering lens'),
        el('p', {}, project.presentation.annotations[lens]),
      )
    : null;

  const techPills = project.technologies?.length
    ? el('div', { class: 'case-tech' },
        project.technologies.map((t) => el('span', {}, t)))
    : null;

  const FAMILY_MAP = {
    netweave: 'netweave', sharecli: 'sharecli', omniroute: 'omniroute',
    'gmk-arch': 'physical', witf: 'physical', 'dss-cipher': 'physical',
    substrate: 'substrate', 'phenotype-omlx': 'omlx',
  };
  const family = FAMILY_MAP[project.slug];

  const familyAccentBar = family
    ? el('div', { class: 'hero-accent-bar', 'aria-hidden': 'true' })
    : null;

  const heroEyebrow = el('p', { class: 'eyebrow' }, project.category + ' \u00b7 ' + project.status);
  const heroTitle = el('h1', {}, project.title);
  const heroLede = el('p', { class: 'lede' }, project.summary);
  const heroMeta = el('div', { class: 'hero-meta' }, heroEyebrow, heroTitle, heroLede, techPills, metrics);

  const heroImage = project.gallery?.[0]
    ? (() => {
        const asset = project.presentation?.assets?.find((entry) => entry.src === project.gallery[0]);
        return el('figure', { class: 'case-hero' },
          el('img', {
            src: project.gallery[0],
            alt: asset?.alt ?? project.presentation?.alt ?? `${project.title} project visual`,
            loading: 'eager',
            decoding: 'async',
            width: asset?.width ?? project.presentation?.media?.width ?? 1600,
            height: asset?.height ?? project.presentation?.media?.height ?? 900,
          }),
          asset?.alt ? el('figcaption', {}, asset.alt) : null,
        );
      })()
    : null;

  const heroPlate = el('div', { class: 'hero-plate' },
    familyAccentBar,
    heroMeta,
    heroImage || el('div', { class: 'hero-plate__placeholder' }),
  );

  const caseStudyAttrs = { class: 'view active portfolio-view case-study' };
  if (family) {
    caseStudyAttrs['data-family'] = family;
    caseStudyAttrs.style = `--family-accent: var(--family-${family}-active, var(--family-${family}))`;
  }

  root.replaceChildren(
    el('section', caseStudyAttrs,
      el('a', { href: '/work', class: 'back-link' }, '\u2190 Back to work'),
      heroPlate,
      project.gallery?.length > 1
        ? el('div', { class: 'case-gallery' },
            project.gallery.map((src) => {
              const asset = project.presentation?.assets?.find((entry) => entry.src === src);
              return el('img', {
                src,
                alt: asset?.alt ?? project.presentation?.alt ?? `${project.title} project visual`,
                loading: 'lazy',
                width: asset?.width ?? project.presentation?.media?.width ?? 1600,
                height: asset?.height ?? project.presentation?.media?.height ?? 900,
              });
            }))
        : null,
      lensAnnotation,
      el('div', { class: 'case-copy' },
        overview, diagram, netweaveField, shareCliWorkbench, substratePlate,
        sections.map(([heading, copy]) =>
          el('div', { class: 'case-section' }, el('h2', {}, heading), el('p', {}, copy))),
        disclosure, evidence,
        project.provenance ? el('p', {}, project.provenance) : null,
        evidencePanel,
      ),
      project.repo ? el('a', { href: project.repo, target: '_blank', rel: 'noreferrer', class: 'text-link' }, 'View repository') : null,
    ),
  );
}


