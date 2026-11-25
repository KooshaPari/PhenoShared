/* ================================================================
   image-slider.js — Draggable before/after image comparison slider.

   Design tokens: teal #7EBAB5, ink #171a18
   Behavior: clip-path inset on top image, drag/touch/keyboard control
   ================================================================ */

/** @returns {boolean} True if user prefers reduced motion. */
function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Initialise a single `.image-slider` element.
 * Reads `data-before`, `data-after`, `data-label-before`, `data-label-after`.
 * @param {HTMLElement} root
 */
function attachSlider(root) {
  if (root._sliderAttached) return; // guard against double-init
  root._sliderAttached = true;

  const beforeSrc = root.getAttribute('data-before') || '';
  const afterSrc = root.getAttribute('data-after') || '';
  const labelBeforeText = root.getAttribute('data-label-before') || 'Before';
  const labelAfterText = root.getAttribute('data-label-after') || 'After';

  // Build DOM
  root.innerHTML = '';

  const imgAfter = mkImg('image-slider__after', afterSrc, 'After');
  const imgBefore = mkImg('image-slider__before', beforeSrc, 'Before');

  const divider = document.createElement('div');
  divider.className = 'image-slider__divider';

  const handle = document.createElement('div');
  handle.className = 'image-slider__handle';
  handle.setAttribute('role', 'presentation');
  divider.appendChild(handle);

  const labelBefore = mkLabel('image-slider__label image-slider__label--before', labelBeforeText);
  const labelAfter = mkLabel('image-slider__label image-slider__label--after', labelAfterText);

  root.append(imgAfter, imgBefore, divider, labelBefore, labelAfter);

  // ARIA on root (slider container)
  root.setAttribute('role', 'slider');
  root.setAttribute('aria-label', 'Image comparison slider');
  root.setAttribute('aria-valuemin', '0');
  root.setAttribute('aria-valuemax', '100');
  root.setAttribute('aria-valuenow', '50');
  root.setAttribute('tabindex', '0');

  let pct = 50;
  let animating = false;

  // -- Core render --------------------------------------------------------
  function render(value) {
    pct = clamp(value, 0, 100);
    root.style.setProperty('--slider-pct', `${pct}%`);
    root.setAttribute('aria-valuenow', Math.round(pct));
    // Clip the "before" (top) image to the left portion only
    imgBefore.style.clipPath = `inset(0 ${100 - pct}% 0 0)`;
  }

  // -- Pointer / touch ----------------------------------------------------
  function onPointerDown(e) {
    if (animating) return;
    e.preventDefault();
    root.setPointerCapture(e.pointerId);
    root.addEventListener('pointermove', onPointerMove);
    root.addEventListener('pointerup', onPointerUp);
    root.addEventListener('pointercancel', onPointerUp);
    root.classList.add('is-dragging');
  }

  function onPointerMove(e) {
    const rect = root.getBoundingClientRect();
    const x = e.clientX - rect.left;
    render((x / rect.width) * 100);
  }

  function onPointerUp(e) {
    root.releasePointerCapture(e.pointerId);
    root.removeEventListener('pointermove', onPointerMove);
    root.removeEventListener('pointerup', onPointerUp);
    root.removeEventListener('pointercancel', onPointerUp);
    root.classList.remove('is-dragging');
  }

  root.addEventListener('pointerdown', onPointerDown);

  // -- Keyboard -----------------------------------------------------------
  root.addEventListener('keydown', (e) => {
    const step = e.shiftKey ? 10 : 2;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault();
      render(pct + step);
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault();
      render(pct - step);
    } else if (e.key === 'Home') {
      e.preventDefault();
      render(0);
    } else if (e.key === 'End') {
      e.preventDefault();
      render(100);
    }
  });

  // -- Entrance animation -------------------------------------------------
  function animateEntrance() {
    if (prefersReducedMotion()) {
      render(50);
      return;
    }

    animating = true;
    render(30);

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            observer.disconnect();
            smoothSlideTo(50, () => {
              animating = false;
            });
            break;
          }
        }
      },
      { threshold: 0.3 }
    );
    observer.observe(root);
  }

  // Smooth slide from current pct to target using requestAnimationFrame
  function smoothSlideTo(target, onDone) {
    const duration = prefersReducedMotion() ? 0 : 420;
    if (duration === 0) {
      render(target);
      if (onDone) onDone();
      return;
    }
    const start = performance.now();
    const from = pct;
    function tick(now) {
      const t = clamp((now - start) / duration, 0, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - t, 3);
      render(from + (target - from) * eased);
      if (t < 1) {
        requestAnimationFrame(tick);
      } else {
        if (onDone) onDone();
      }
    }
    requestAnimationFrame(tick);
  }

  // Kick off
  animateEntrance();
}

// ---- Helpers -------------------------------------------------------------

function mkImg(cls, src, alt) {
  const img = document.createElement('img');
  img.className = cls;
  img.src = src;
  img.alt = alt;
  img.draggable = false;
  return img;
}

function mkLabel(cls, text) {
  const span = document.createElement('span');
  span.className = cls;
  span.textContent = text;
  span.setAttribute('aria-hidden', 'true');
  return span;
}

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

// ---- Public API ----------------------------------------------------------

/**
 * Auto-find all `.image-slider` elements and initialise them.
 * Call once on page load or after dynamic insert.
 */
export function initImageSliders() {
  document.querySelectorAll('.image-slider').forEach(attachSlider);
}
