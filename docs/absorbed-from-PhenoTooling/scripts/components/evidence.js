import { el } from './dom.js';

// Public summaries describe source types without exposing internal ledger names.
export function publicEvidenceSummary(record) {
  switch (record.evidence) {
    case 'github-pass1-after.md': return 'Repository documentation and project history';
    case 'EVIDENCE_LEDGER.md': return 'Retained project records';
    case 'omniroute-evidence-ledger.md': return 'Upstream contribution records';
    default: return 'Supporting project evidence is being assembled';
  }
}

function preferredMetric(record, lens) {
  if (!record.metrics?.length) return null;
  const index = lens === 'product' && record.metrics.length > 1 ? 1 : 0;
  return record.metrics[index];
}

export function metricAnnotation(record, lens) {
  const metric = preferredMetric(record, lens);
  if (!metric) return null;

  const [value, label, qualification] = metric;
  return el(
    'div',
    { class: 'metric-annotation', role: 'note', 'aria-label': `${label}: ${value}` },
    el('strong', {}, value),
    el('span', {}, label),
    el('small', {}, qualification),
  );
}

export function evidenceLabel(record, lens) {
  const label = lens === 'product' ? 'Product evidence' : 'Engineering evidence';
  const assets = record.presentation?.assets ?? [];
  return el(
    'p',
    { class: 'evidence-label' },
    el('span', {}, label),
    el('strong', {}, publicEvidenceSummary(record)),
    assets.length
      ? el(
          'small',
          {},
          `Selected media: ${assets.length} manifest-traced ${assets.length === 1 ? 'file' : 'files'}; ownership and licensing review pending.`,
        )
      : null,
  );
}

export const createMetricAnnotation = metricAnnotation;
export const createEvidenceLabel = evidenceLabel;
