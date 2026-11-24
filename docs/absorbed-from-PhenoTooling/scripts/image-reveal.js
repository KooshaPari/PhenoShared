/**
 * image-reveal.js — Image load choreography with stylish reveal animations.
 *
 * Detects all <img> elements on page load and via MutationObserver.
 * Supports data-src lazy loading, data-reveal-style hints, and
 * respects prefers-reduced-motion.
 *
 * Export: initImageReveal()
 */

const REVEAL_STYLES = ['wipe-right', 'zoom-fade', 'curtain', 'pixelate'];
const TRANSITION_DURATION = 800;
const EASING = 'cubic-bezier(0.16, 1, 0.3, 1)';

/**
 * Check whether the user prefers reduced motion.
 * @returns {boolean}
 */
function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Pick a reveal style: use data-reveal-style if set, otherwise random.
 * @param {HTMLImageElement} img
 * @returns {string}
 */
function pickRevealStyle(img) {
  const attr = img.getAttribute('data-reveal-style');
  if (attr && REVEAL_STYLES.includes(attr)) return attr;
  return REVEAL_STYLES[Math.floor(Math.random() * REVEAL_STYLES.length)];
}

/**
 * Set up clip-path / filter transitions on an image element.
 * @param {HTMLImageElement} img
 * @param {string} style
 */
function applyRevealStyle(img, style) {
  img.setAttribute('data-reveal-style', style);

  switch (style) {
    case 'wipe-right':
      // Start hidden: inset from left
      img.style.clipPath = 'inset(0 100% 0 0)';
      img.style.transition = 'none';
      // Force reflow
      void img.offsetHeight;
      img.style.transition = `clip-path ${TRANSITION_DURATION}ms ${EASING}`;
      requestAnimationFrame(() => {
        img.style.clipPath = 'inset(0)';
      });
      break;

    case 'zoom-fade':
      img.style.transform = 'scale(1.05)';
      img.style.filter = 'blur(10px)';
      img.style.opacity = '0';
      img.style.transition = 'none';
      void img.offsetHeight;
      img.style.transition = [
        `transform ${TRANSITION_DURATION}ms ${EASING}`,
        `filter ${TRANSITION_DURATION}ms ${EASING}`,
        `opacity ${TRANSITION_DURATION}ms ${EASING}`,
      ].join(', ');
      requestAnimationFrame(() => {
        img.style.transform = 'scale(1)';
        img.style.filter = 'blur(0)';
        img.style.opacity = '1';
      });
      break;

    case 'curtain':
      img.style.clipPath = 'polygon(50% 50%, 50% 50%, 50% 50%, 50% 50%)';
      img.style.transition = 'none';
      void img.offsetHeight;
      img.style.transition = `clip-path ${TRANSITION_DURATION}ms ${EASING}`;
      requestAnimationFrame(() => {
        img.style.clipPath = 'polygon(0 0, 100% 0, 100% 100%, 0 100%)';
      });
      break;

    case 'pixelate':
      // Simulate pixelate via contrast + saturate filter stepping
      img.style.filter = 'contrast(20) saturate(0) blur(6px)';
      img.style.opacity = '0';
      img.style.transition = 'none';
      void img.offsetHeight;
      img.style.transition = [
        `filter ${TRANSITION_DURATION}ms ${EASING}`,
        `opacity ${TRANSITION_DURATION}ms ${EASING}`,
      ].join(', ');
      requestAnimationFrame(() => {
        img.style.filter = 'contrast(1) saturate(1) blur(0)';
        img.style.opacity = '1';
      });
      break;
  }
}

/**
 * Remove inline transition styles so the image renders normally after reveal.
 * @param {HTMLImageElement} img
 */
function cleanupAfterReveal(img) {
  setTimeout(() => {
    img.style.clipPath = '';
    img.style.transform = '';
    img.style.filter = '';
    img.style.opacity = '';
    img.style.transition = '';
  }, TRANSITION_DURATION + 50);
}

/**
 * Create the container + placeholder around a bare <img>.
 * @param {HTMLImageElement} img
 * @returns {HTMLDivElement} The container element.
 */
function wrapImage(img) {
  // Already wrapped
  if (img.parentElement && img.parentElement.classList.contains('image-reveal-container')) {
    return img.parentElement;
  }

  const container = document.createElement('div');
  container.className = 'image-reveal-container';

  // Propagate intrinsic dimensions so the container reserves space
  // before the image loads (prevents CLS).
  const w = parseInt(img.getAttribute('width'), 10);
  const h = parseInt(img.getAttribute('height'), 10);
  if (w > 0 && h > 0) {
    container.style.setProperty('--reveal-aspect', `${w} / ${h}`);
  }

  // Insert container before the image, then move image into it
  img.parentElement.insertBefore(container, img);
  container.appendChild(img);

  // Build placeholder — sample the image's current colour or use paper
  const placeholder = document.createElement('div');
  placeholder.className = 'image-reveal-placeholder';
  placeholder.setAttribute('aria-hidden', 'true');
  container.insertBefore(placeholder, img);

  // If image has an immediate src, use it as blurred backdrop
  if (img.src && !img.src.startsWith('data:')) {
    placeholder.style.backgroundImage = `url(${img.src})`;
  }

  // Mark image for styling
  img.classList.add('image-reveal-img');

  return container;
}

/**
 * Observe an <img> for load and reveal it.
 * @param {HTMLImageElement} img
 */
function observeImage(img) {
  // Handle data-src lazy-load pattern
  if (img.dataset.src && !img.src) {
    const realSrc = img.dataset.src;
    img.removeAttribute('data-src');

    // Create a temporary Image to preload the real source
    const preloader = new Image();
    preloader.onload = () => {
      img.src = realSrc;
      revealImage(img);
    };
    preloader.src = realSrc;
    return;
  }

  // If already loaded (cached)
  if (img.complete && img.naturalWidth > 0) {
    wrapImage(img);
    revealImage(img);
    return;
  }

  // Wait for the load event
  const onLoad = () => {
    img.removeEventListener('load', onLoad);
    wrapImage(img);
    revealImage(img);
  };
  img.addEventListener('load', onLoad);

  // Handle error gracefully — still reveal without animation
  img.addEventListener('error', () => {
    img.removeEventListener('load', onLoad);
    wrapImage(img);
    img.classList.add('image-reveal-img');
    const container = img.closest('.image-reveal-container');
    const ph = container?.querySelector('.image-reveal-placeholder');
    if (ph) ph.classList.add('loaded');
  }, { once: true });
}

/**
 * Trigger the reveal animation on a loaded image.
 * @param {HTMLImageElement} img
 */
function revealImage(img) {
  const container = img.closest('.image-reveal-container');
  const placeholder = container?.querySelector('.image-reveal-placeholder');

  if (prefersReducedMotion()) {
    // Instant show — no animation
    img.classList.add('image-reveal-img');
    if (placeholder) placeholder.classList.add('loaded');
    return;
  }

  const style = pickRevealStyle(img);
  applyRevealStyle(img, style);

  // Fade out placeholder after a short stagger
  setTimeout(() => {
    if (placeholder) placeholder.classList.add('loaded');
  }, 80);

  cleanupAfterReveal(img);
}

/**
 * Scan the DOM for unprocessed images and start observing them.
 * @param {Element} [root=document.body]
 */
function scanImages(root = document.body) {
  const images = root.querySelectorAll('img:not([data-reveal-processed])');
  images.forEach((img) => {
    img.setAttribute('data-reveal-processed', 'true');
    observeImage(img);
  });
}

/**
 * Initialize image reveal choreography.
 *
 * Call once on page load. Sets up MutationObserver to handle
 * dynamically added images (e.g. SPA route transitions).
 *
 * @returns {{ disconnect: () => void }} Call disconnect() to tear down.
 */
export function initImageReveal() {
  // Initial scan
  scanImages();

  // Watch for new images (SPA navigation, lazy components)
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (node.nodeType === Node.ELEMENT_NODE) {
          if (node.tagName === 'IMG') {
            scanImages(node);
          } else if (node.querySelectorAll) {
            scanImages(node);
          }
        }
      }

      // Re-scan on attribute changes (e.g. src updated for lazy load)
      if (mutation.type === 'attributes' && mutation.attributeName === 'src') {
        const el = mutation.target;
        if (el.tagName === 'IMG' && el.getAttribute('data-reveal-processed')) {
          // Re-trigger reveal for src changes (lazy load swap)
          el.removeAttribute('data-reveal-processed');
          observeImage(el);
        }
      }
    }
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['src', 'data-src'],
  });

  return {
    disconnect() {
      observer.disconnect();
    },
  };
}
