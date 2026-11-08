import { el } from '../components/dom.js';

export function canLoadModel({ modelUrl, webglAvailable = false, reducedMotion = false } = {}) {
  return Boolean(modelUrl && webglAvailable && !reducedMotion);
}

export function createModelSlot({ posterSrc, posterAlt, width, height, modelUrl } = {}) {
  const status = modelUrl ? 'Interactive model available on supported devices.' : 'Static poster; an interactive model has not been supplied.';
  return el('figure', { class: 'model-slot' },
    posterSrc ? el('img', { src: posterSrc, alt: posterAlt, width, height, loading: 'lazy', decoding: 'async' }) : null,
    el('figcaption', { class: 'model-slot__status' }, status),
  );
}
