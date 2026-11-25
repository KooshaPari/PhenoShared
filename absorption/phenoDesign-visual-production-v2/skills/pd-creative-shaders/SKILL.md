---
name: pd-creative-shaders
description: "Build procedural 2D/3D effects, particles and material experiments that remain controllable and affordable."
license: MIT (original guidance; linked tools and assets keep their own licenses)
---

# Creative Shaders

Specify the visual effect in perceptual terms before choosing GLSL, WGSL, canvas, CSS or an engine graph. Decide whether the effect communicates material, spatial structure or an interaction; avoid expensive shaders that merely decorate every surface. Start from a flat/static reference and a measured budget.

Parameterize relevant artistic controls with bounded values. Keep a deterministic seed and a fixed-time capture mode for validation while preserving real-time responsiveness in the product. Separate simulation from rendering; record update cadence, resolution scaling and precision assumptions. Check alpha/compositing and color-space transitions explicitly.

Integrate pointer/scroll/time through a single owner rather than competing animation clocks. Pause when not visible, release textures/programs/listeners on teardown, and implement a lower-cost or static fallback. Test mobile/low-capability behavior, context loss, resize and repeated mount/unmount.

For reusable shader/graphics infrastructure, extend phenotype-gfx instead of introducing a parallel SDK in phenoDesign. PhenoDesign owns the design recipes, integration and quality bar. A shader compiling on one driver does not prove cross-device visual or performance equivalence; retain actual frame captures and measurements.

## Related contracts

Read the repository's `docs/visual-production/E2E-CONTRACT.md`, `ALL-FORMS.md`, and source catalog for the selected tool. In the standalone kit these are under `docs/` and `resources/`. Preserve exact failure/blocked states and the existing source/evidence owners.
