import { el } from './dom.js';
import { createLayeredImage } from '../media/layered-image.js';
import { renderOmniRouteTopology } from '../media/omniroute-topology.js';
import {
  createEvidenceLabel,
  createMetricAnnotation,
  evidenceLabel,
  metricAnnotation,
} from './evidence.js';

function annotation(record, lens) {
  return record.presentation?.annotations?.[lens]
    ?? record.presentation?.annotations?.engineering
    ?? record.summary;
}

function artifactHeader(record, label) {
  return el(
    'header',
    { class: 'artifact-header' },
    el('p', { class: 'atelier-label' }, label),
    el('h2', {}, el('a', { href: `/work/${record.slug}` }, record.title)),
    el('p', { class: 'artifact-summary' }, record.summary),
  );
}

function annotationBlock(record, lens) {
  return el(
    'div',
    { class: 'artifact-annotation' },
    el('span', { 'aria-hidden': 'true' }, lens === 'product' ? 'P' : 'E'),
    el('p', {}, annotation(record, lens)),
  );
}

export function artifactTextSummary(record) {
  return record.presentation?.alt ?? record.summary;
}

export function physicalPlate(record, lens) {
  const media = record.presentation?.media ?? {};
  const selectedAsset = record.presentation?.assets?.[0];
  const image = selectedAsset?.src ?? record.gallery?.[0];

  return el(
    'article',
    { class: `artifact artifact--physical artifact--${record.slug}`, 'data-artifact': record.slug, 'data-reveal': 'up', 'data-reveal-delay': '0' },
    artifactHeader(record, 'Material artifact'),
    image
      ? el(
          'figure',
          { class: 'artifact-media artifact-media--physical' },
          record.slug === 'witf'
            ? createLayeredImage({
                src: image,
                alt: record.presentation.alt,
                width: selectedAsset?.width ?? media.width,
                height: selectedAsset?.height ?? media.height,
                layers: [{ label: 'shadow', className: 'layered-image__layer--shadow' }],
                className: 'artifact-media__layered',
              })
            : el('img', {
            src: image,
            alt: record.presentation.alt,
            width: selectedAsset?.width ?? media.width,
            height: selectedAsset?.height ?? media.height,
            loading: record.slug === 'witf' ? 'eager' : 'lazy',
            decoding: 'async',
            ...(record.slug === 'witf' ? { fetchpriority: 'high' } : {}),
            }),
          el('figcaption', {}, `${record.category} / ${record.status}`),
        )
      : null,
    el(
      'div',
      { class: 'artifact-context' },
      annotationBlock(record, lens),
      metricAnnotation(record, lens),
    ),
  );
}

function topologyLabels(record) {
  if (record.slug === 'substrate') {
    return ['HTTP / CLI / MCP / A2A', 'policy + budget', 'health + fallback', 'provider execution'];
  }
  return ['agent bursts', 'process observation', 'coalesce + queue', 'shared host state'];
}

export function systemsSheet(record, lens) {
  const labels = topologyLabels(record);
  const summaryId = `artifact-${record.slug}-summary`;

  return el(
    'article',
    { class: `artifact artifact--systems artifact--${record.slug}`, 'data-artifact': record.slug, 'data-reveal': 'up', 'data-reveal-delay': '100' },
    artifactHeader(record, record.slug === 'omniroute' ? 'Upstream routing overview' : record.slug === 'substrate' ? 'Policy routing sheet' : 'Runtime topology'),
    record.slug === 'omniroute' ? renderOmniRouteTopology(lens) : el(
      'div',
      {
        class: 'systems-diagram',
        role: 'img',
        'aria-label': record.presentation.alt,
        'aria-describedby': summaryId,
      },
      labels.map((label, index) => [
        el(
          'div',
          { class: 'systems-node' },
          el('span', {}, String(index + 1).padStart(2, '0')),
          el('strong', {}, label),
        ),
        index < labels.length - 1
          ? el('span', { class: 'systems-route', 'aria-hidden': 'true' }, '->')
          : null,
      ]),
    ),
    el('p', { class: 'artifact-text-summary', id: summaryId }, artifactTextSummary(record)),
    el(
      'div',
      { class: 'artifact-context' },
      annotationBlock(record, lens),
      metricAnnotation(record, lens),
    ),
  );
}

function experimentRows(record) {
  if (record.slug === 'netweave') {
    return [
      ['Route layer', 'A* over directed road graph'],
      ['Traffic layer', 'Per-road cellular automata'],
      ['Observed', 'Congestion, waves, gridlock'],
      ['Boundary', 'Congestion-aware rerouting remained future work'],
    ];
  }
  return [
    ['Upstream', 'jundot/omlx / attributed'],
    ['Fork delta', 'Routing + Rust performance cores'],
    ['Method', 'Backend comparison + evaluation'],
    ['Boundary', 'Research scope / support varies'],
  ];
}

export function experimentNote(record, lens) {
  const summaryId = `artifact-${record.slug}-summary`;
  return el(
    'article',
    { class: `artifact artifact--experiment artifact--${record.slug}`, 'data-artifact': record.slug, 'data-reveal': 'up', 'data-reveal-delay': '200' },
    artifactHeader(record, record.slug === 'netweave' ? 'Simulation field note' : 'Fork-delta experiment'),
    el(
      'div',
      {
        class: 'experiment-sheet',
        role: 'img',
        'aria-label': record.presentation.alt,
        'aria-describedby': summaryId,
      },
      experimentRows(record).map(([term, detail], index) =>
        el(
          'div',
          { class: 'experiment-row' },
          el('span', {}, String(index + 1).padStart(2, '0')),
          el('strong', {}, term),
          el('p', {}, detail),
        ),
      ),
    ),
    el('p', { class: 'artifact-text-summary', id: summaryId }, artifactTextSummary(record)),
    el(
      'div',
      { class: 'artifact-context' },
      annotationBlock(record, lens),
      metricAnnotation(record, lens),
    ),
  );
}

const ARTIFACT_FAMILY_MAP = {
  netweave: 'netweave',
  sharecli: 'sharecli',
  omniroute: 'omniroute',
  'gmk-arch': 'physical',
  witf: 'physical',
  'dss-cipher': 'physical',
  substrate: 'substrate',
  'phenotype-omlx': 'omlx',
};

export function createArtifact(record, lens) {
  const renderers = {
    'physical-plate': physicalPlate,
    'systems-sheet': systemsSheet,
    'experiment-note': experimentNote,
  };
  const render = renderers[record.presentation?.type] ?? systemsSheet;
  const artifact = render(record, lens);

  const family = ARTIFACT_FAMILY_MAP[record.slug];
  if (family) {
    artifact.setAttribute('data-family', family);
    artifact.style.setProperty('--family-accent', `var(--family-${family}-active, var(--family-${family}))`);
  }

  // Category badge overlay on the media area
  if (record.category) {
    const badge = el('span', { class: 'artifact-badge' }, record.category);
    artifact.prepend(badge);
  }

  return artifact;
}

export {
  createEvidenceLabel,
  createMetricAnnotation,
  evidenceLabel,
  metricAnnotation,
};

export const createPhysicalPlate = physicalPlate;
export const createSystemsSheet = systemsSheet;
export const createExperimentNote = experimentNote;
