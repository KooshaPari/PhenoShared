---
name: fd3d-scroll-story
description: "Create reversible, scroll-linked 3D product storytelling with rotation, exploded views, material reveals and native page navigation; use for Apple/Nike-like premium product interactions."
license: MIT
metadata:
  version: "1.0"
  origin: "original-kit-skill"
---

# One normalized timeline, one transform owner

## State model
Separate story progress, user orbit offset, current material selection and accessibility policy. Compute scroll progress from a stable section range and clamp it to 0..1. Derive object pose and part offsets from that value; do not accumulate rotations on scroll events.

## Recipe
1. Write three beats: silhouette → construction → finish. Specify what each beat teaches and its required object nodes.
2. Keep a semantic DOM page and native sticky stage. Make the page readable without the renderer.
3. Choose one controller: a native progress calculation, GSAP ScrollTrigger, Motion scroll, or R3F/Drei where appropriate. Do not let several systems own rotation or create multiple smooth-scroll roots.
4. Interpolate absolute states. Use quaternions for general rotations; explicit continuous yaw is valid for a designed multi-turn orbit. Test reverse scroll and arbitrary seek.
5. Give each exploded component a stable rest transform and local-space displacement. Avoid animation that turns scale into a substitute for disassembly.
6. Put manual orbit in a separate parent/offset layer. Decide whether controls temporarily override, pause or add to the story. Provide an explicit reset.
7. Recompute range on layout changes. Watch sticky ancestors, mobile viewport changes, images and font loading. Never intercept ordinary scroll solely to force a cinematic effect.
8. Pause/freeze or remove the narrative scrub under reduced motion. Offer equivalent direct controls and complete text. No scroll-controlled product feature may be the only way to access necessary information.

## Gate
Seek 0→1→0 gives the same state. Resize at mid-story does not jump to an invalid pose. Offscreen/hidden render loops stop. No infinite loading canvas. Test input with mouse, touch and keyboard.

Sources: R10, R11, R12, R13. See `demo/`, `integrations/three-gsap/` and `recipes/sneaker-story.md`.

## Kit location
Kit root: `{{KIT_ROOT}}`. The sync script expands this token. In the canonical ZIP, resolve the root two directories above this skill folder. Paths mentioned above are relative to that root. Read only the referenced files needed for the task.
