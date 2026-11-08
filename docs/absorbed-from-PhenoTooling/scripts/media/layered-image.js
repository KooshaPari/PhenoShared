import { el } from '../components/dom.js';

export function supportsLayeredMotion({ reducedMotion = false, coarsePointer = false } = {}) {
  return !reducedMotion && !coarsePointer;
}

export function createLayeredImage({ src, alt, width, height, layers = [], className = '' }) {
  const image = el('img', { src, alt, width, height, loading: 'eager', decoding: 'async', fetchpriority: 'high' });
  return el('figure', { class: `layered-image ${className}` }, image,
    layers.map(({ label, className: layerClass = '' }) => el('span', { class: `layered-image__layer ${layerClass}`, 'aria-hidden': 'true', 'data-layer': label ?? '' })),
  );
}
