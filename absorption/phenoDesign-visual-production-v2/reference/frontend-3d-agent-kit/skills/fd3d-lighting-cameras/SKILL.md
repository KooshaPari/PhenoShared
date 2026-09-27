---
name: fd3d-lighting-cameras
description: "Art-direct product lighting, camera poses and semantic close-ups; use to make locally created 3D look intentional rather than like an unlit CAD viewport."
license: MIT
metadata:
  version: "1.0"
  origin: "original-kit-skill"
---

# Light the story, not every surface equally

Start with a neutral clay render and a large key light. Place a fill only where it preserves detail, then a rim where separation is necessary. If all surfaces have identical brightness, material work will be hard to judge.

## Shot process
1. Define a hero frame that shows the product's characteristic silhouette with safe copy space.
2. Define a construction frame that exposes actual named parts without hiding them behind one another.
3. Define a material frame whose distance justifies detail. Do not fly through a surface that has no close-up topology.
4. Keep focal length and framing consistent enough to orient the viewer. Camera dolly, object rotation and field-of-view changes are different tools; avoid using all three without a reason.
5. Fix clipping planes to the scale, avoid intersections, and account for vertical mobile framing. Do not simply crop the desktop viewport.
6. Keep lighting stable across scroll unless a light change itself teaches the product story. A camera orbit through an environment should not make the brand color disappear.
7. Generate an image contact sheet at 0%, 25%, 50%, 75%, 100% progress and both extremes of manual control.

## Quality checks
No clipped toe/collar/handle at any target viewport. No glaring untextured back side. Transparent materials have useful reflected structure. Compare flat/clay and final renders; if the former is clearer, fix lighting rather than adding bloom.

Sources: R05, R08, R19. See `contracts/story.json` and `resources/QUALITY-GATES.md`.

## Kit location
Kit root: `{{KIT_ROOT}}`. The sync script expands this token. In the canonical ZIP, resolve the root two directories above this skill folder. Paths mentioned above are relative to that root. Read only the referenced files needed for the task.
