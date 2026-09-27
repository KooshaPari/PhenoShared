---
name: pd-interactive-2d
description: "Build input-driven SVG, Canvas and 2.5D props with usable semantics and deterministic interaction."
license: MIT (original guidance; linked tools and assets keep their own licenses)
---

# Interactive 2D

Define the prop's purpose and state before choosing SVG, Canvas, PixiJS or a rigged runtime. SVG is often sufficient for knobs, diagrams, layered product cutaways and path morphs; Canvas becomes useful for many animated elements. A CSS perspective transform is not proof of full 3D geometry.

Use one state model for pointer, touch, keyboard and accessible controls. Keep animation separate from business logic. Capture/release pointers correctly, preserve page scrolling outside the interaction, and define what happens on pointercancel, blur and unmount. A scroll-linked object should explain an actual product property, not hijack the entire page.

Build reduced-motion and static states from the same content model. Pause offscreen/hidden work and avoid redraw loops for settled content. Clamp user-controlled values and preserve state if graphics initialization fails. Essential content remains DOM-accessible.

Use the supplied vector-prop canary to test state and geometry, not as a finished brand design. Acceptance requires forward/reverse interaction, interruption, resize, keyboard operation, fallback, no stale listeners and real screenshots at target sizes. Compare whether a static diagram would communicate as well before accepting runtime complexity.

## Related contracts

Read the repository's `docs/visual-production/E2E-CONTRACT.md`, `ALL-FORMS.md`, and source catalog for the selected tool. In the standalone kit these are under `docs/` and `resources/`. Preserve exact failure/blocked states and the existing source/evidence owners.
