---
name: fd3d-medium-selection
description: "Choose between CSS, SVG, Rive, a pre-rendered sequence, model-viewer and custom 3D; use before committing a frontend to a heavyweight renderer."
license: MIT
metadata:
  version: "1.0"
  origin: "original-kit-skill"
---

# Choose the lightest medium that preserves the idea

Build a small falsification test, not a stack popularity contest. Keep content and controls in semantic HTML regardless of rendering medium.

## Decision ladder
- Ordinary hover, reveal, spacing, depth illusion: CSS transforms, native scroll-linked CSS where supported, or Motion. Avoid a canvas.
- Articulated vector mascot, icon or control: SVG or Rive state machine. The editable vector/state-machine source matters as much as the export.
- Locked camera, no meaningful manipulation: pre-render a short sequence/video and supply a poster. Measure decoded memory and seek cost; do not preload hundreds of full-resolution frames.
- Rotate/zoom a single product: evaluate model-viewer before writing a scene engine.
- Exploded parts, custom materials, camera choreography or real spatial interaction: Three.js, with React Three Fiber when React lifecycle integration is valuable.
- Heavy local look development or source modeling: Blender. Its render output is not automatically the right browser runtime.

## Experiment
Implement the key beat with both your preferred medium and one simpler alternative. Compare legibility, transfer, startup, interaction fidelity, authoring iteration time and failure behavior. Record what 3D buys that a static image cannot. If the answer is only "looks advanced", reduce scope or reconsider the medium.

## Gate
One authoritative animation clock; one renderer owner; a declared no-JS/no-WebGL/low-motion path. Do not stack Lenis, GSAP, Motion and R3F scroll controllers on the same property. Do not make smooth scrolling a prerequisite for ordinary navigation.

Sources: R08, R10, R11, R12, R13, R14, R15. See `resources/STACK-CHOICES.md` and `recipes/2-5d-fallback.md`.

## Kit location
Kit root: `{{KIT_ROOT}}`. The sync script expands this token. In the canonical ZIP, resolve the root two directories above this skill folder. Paths mentioned above are relative to that root. Read only the referenced files needed for the task.
