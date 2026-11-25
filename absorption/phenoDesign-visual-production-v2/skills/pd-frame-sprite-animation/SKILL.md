---
name: pd-frame-sprite-animation
description: "Produce frame-by-frame 2D animation, spritesheets, animated illustration and efficient runtime atlases."
license: MIT (original guidance; linked tools and assets keep their own licenses)
---

# Frame Sprite Animation

Select frame animation when drawn deformation, texture or timing is central rather than forcing everything through a vector rig. Keep a timeline source with layers/cels, consistent pivots, frame durations and a palette/alpha contract. Krita, dedicated sprite editors and Grease Pencil are candidates; qualify the specific application's batch or scripting path before calling it unattended.

Create key poses first, then breakdowns and in-betweens. Decide whether frames intentionally hold on twos/threes or target continuous interpolation; do not duplicate frames blindly to claim a higher framerate. For sprites, specify logical canvas size, trimming, padding, extrusion and anchor metadata alongside the atlas image.

Check alpha edges under linear filtering and neighboring atlas frames under minification. Do not pack a texture larger than the tested runtime budget. Export a static poster and an accessible state description when an animation communicates status.

A valid PNG sequence is only an intermediate. Verify ordering, missing/duplicate unintended frames, loop seam, actual playback cadence, state interruption, scale and mobile memory. Preserve original source, frame manifest, export recipe and atlas metadata. For instructional evidence, retain original timing and label any speed change in presentation derivatives.

## Related contracts

Read the repository's `docs/visual-production/E2E-CONTRACT.md`, `ALL-FORMS.md`, and source catalog for the selected tool. In the standalone kit these are under `docs/` and `resources/`. Preserve exact failure/blocked states and the existing source/evidence owners.
