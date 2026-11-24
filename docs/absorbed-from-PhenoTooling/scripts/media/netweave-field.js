export function createNetWeaveFrame(seed = 1, count = 12) {
  let state = seed >>> 0;
  const next = () => { state = (state * 1664525 + 1013904223) >>> 0; return state / 2 ** 32; };
  return Array.from({ length: count }, (_, index) => ({ id: index, x: Math.round(next() * 100), y: Math.round(next() * 100), congestion: Math.round(next() * 3) }));
}

export function renderNetWeaveField(documentRef = document, { controller, states } = {}) {
  const entries = states ?? [
    { label: 'Open gaps', description: 'Three following vehicles have open gaps before the stationary lead vehicle.', altText: 'Four low-profile vehicle objects on a marked road; three following vehicles sit two cells behind a stationary lead vehicle at the rightmost cell.', image: '/public/projects/netweave/desktop-01-v3.webp', mobileImage: '/public/projects/netweave/mobile-01-v3.webp', objectLabel: 'Three following vehicles sit two cells behind the stationary lead vehicle.', relationship: 'Each following vehicle keeps an open gap before the stationary lead vehicle.' },
    { label: 'Gaps narrow', description: 'The following vehicles advance one cell; the lead vehicle stays fixed.', altText: 'Four low-profile vehicle objects on a marked road; three following vehicles have closed to one cell behind the stationary lead vehicle at the rightmost cell.', image: '/public/projects/netweave/desktop-02-v3.webp', mobileImage: '/public/projects/netweave/mobile-02-v3.webp', objectLabel: 'Three following vehicles close to one cell behind the stationary lead vehicle.', relationship: 'Each following vehicle advances one cell; the stationary lead vehicle stays fixed.' },
    { label: 'Approach', description: 'The amber vehicle approaches the lead vehicle. No vehicle changes lane or route.', altText: 'Four low-profile vehicle objects on a marked road; the leading following vehicle is adjacent to the stationary lead vehicle at the rightmost cell. No vehicle changes lane or route.', image: '/public/projects/netweave/desktop-03-v3.webp', mobileImage: '/public/projects/netweave/mobile-03-v3.webp', objectLabel: 'The leading following vehicle sits adjacent to the stationary lead vehicle.', relationship: 'The amber following vehicle approaches the stationary lead vehicle. No vehicle changes lane or route.' },
  ];
  const descriptions = entries.map((entry) => entry.description);
  const summary = documentRef.createElement('p');
  summary.className = 'netweave-field__summary';
  summary.textContent = 'Illustrative local-spacing study. Original explanatory artwork, not recorded NetWeave output. The amber vehicle is a following vehicle; the rightmost graphite-grey vehicle stays stationary. Congestion-aware rerouting remained future work.';
  const field = documentRef.createElement('div');
  field.className = 'netweave-specimen';
  const picture = documentRef.createElement('picture');
  const source = documentRef.createElement('source');
  source.media = '(max-width: 600px)';
  source.srcset = entries[0].mobileImage;
  const image = documentRef.createElement('img');
  image.className = 'netweave-field__image';
  image.src = entries[0].image;
  image.alt = entries[0].altText;
  image.width = 1600;
  image.height = 1100;
  image.loading = 'lazy';
  picture.append(source, image);
  const stateText = documentRef.createElement('p');
  stateText.setAttribute('aria-live', 'polite');
  stateText.textContent = `${entries[0].objectLabel} ${entries[0].relationship}`;
  const controls = documentRef.createElement('div');
  controls.setAttribute('role', 'group');
  controls.setAttribute('aria-label', 'Illustrative traffic states');
  const buttons = entries.map((entry, index) => {
    const button = documentRef.createElement('button');
    button.type = 'button';
    button.textContent = entry.label;
    button.setAttribute('aria-pressed', String(index === 0));
    button.style.minHeight = '44px';
    button.style.marginRight = '.5rem';
    button.addEventListener('click', () => controller ? controller.selectState(index) : select(index));
    return button;
  });
  const motionButton = documentRef.createElement('button');
  motionButton.type = 'button';
  motionButton.textContent = 'Enable discrete motion';
  motionButton.setAttribute('aria-pressed', 'false');
  motionButton.setAttribute('aria-label', 'Enable discrete motion by choice');
  let motionEnabled = controller?.isMotionEnabled?.() === true;
  const updateMotion = (enabled) => {
    motionEnabled = enabled === true;
    motionButton.setAttribute('aria-pressed', String(motionEnabled));
    motionButton.textContent = motionEnabled ? 'Disable discrete motion' : 'Enable discrete motion';
  };
  motionButton.addEventListener('click', () => {
    if (controller?.setMotionEnabled) controller.setMotionEnabled(!motionEnabled);
    else updateMotion(!motionEnabled);
  });
  const motionControls = documentRef.createElement('div');
  motionControls.setAttribute('role', 'group');
  motionControls.setAttribute('aria-label', 'Motion preference');
  motionControls.append(motionButton);
  const select = (index) => {
    const entry = entries[index];
    source.srcset = entry.mobileImage;
    image.src = entry.image;
    image.alt = entry.altText;
    stateText.textContent = `${entry.objectLabel} ${entry.relationship}`;
    buttons.forEach((button, selected) => button.setAttribute('aria-pressed', String(selected === index)));
  };
  if (controller) {
    controller.subscribe(({ state, motion }) => { select(state); updateMotion(motion); });
    select(controller.get().state);
  }
  image.addEventListener('error', () => { stateText.textContent = 'Artwork unavailable. ' + descriptions.join(' '); });
  controls.append(...buttons);
  field.append(picture, controls, motionControls, stateText);
  const figure = documentRef.createElement('figure');
  figure.className = 'netweave-field-figure';
  figure.append(field, summary);
  return figure;
}
