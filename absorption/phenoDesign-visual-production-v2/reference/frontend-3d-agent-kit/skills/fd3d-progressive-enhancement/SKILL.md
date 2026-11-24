---
name: fd3d-progressive-enhancement
description: "Preserve accessibility and performance when adding 3D, animated scroll, glass and rich interactions; use for reduced motion, no-JS/no-WebGL and constrained devices."
license: MIT
metadata:
  version: "1.0"
  origin: "original-kit-skill"
---

# The page must survive the spectacle

## Baseline contract
The product's name, value, key construction explanation and primary actions exist in semantic HTML before 3D loads. An accessible static poster or meaningful illustration occupies the visual space. Reserve layout dimensions to avoid jumps.

## Required cases
- JavaScript unavailable: copy/navigation and poster work; unsupported controls are hidden or disabled without suggesting they function.
- WebGL unavailable/context lost: restore the poster and explain the limitation without stranding a blank panel.
- Reduced motion: no scroll-coupled movement by default. Direct user actions may change state immediately. Do not force a long pinned blank narrative.
- Data-saving signal or constrained budget: prefer the poster or lower-detail asset; the browser signal is optional, not universally present.
- Touch: horizontal manipulation must not consume vertical page scrolling. Test pointer cancellation and missing hover.
- Keyboard: meaningful visible focus, real DOM controls, no canvas-only state. Do not trap arrow keys unless the canvas/control has focus.
- Zoom/text growth: content reflows; controls do not overlap the product story or require tiny text.

## Test scope
Automated DOM tests help but do not certify full accessibility. Check motion, legibility and focus visually, and use an appropriate accessibility audit in the target app. Never give a decorative object a misleading interactive role.

Sources: R10, R11, R12, R22. See `tests/browser_smoke.py`. The CPU mesh renderer is a kit inspection fallback; a production site should normally choose a cheap poster over heavy CPU 3D on a no-WebGL device.

## Kit location
Kit root: `{{KIT_ROOT}}`. The sync script expands this token. In the canonical ZIP, resolve the root two directories above this skill folder. Paths mentioned above are relative to that root. Read only the referenced files needed for the task.
