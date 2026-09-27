---
name: fd3d-shader-effects
description: "Design bounded shader effects such as refractive lenses, distortion, iridescence and product reveals; use only after geometry, composition and basic materials work."
license: MIT
metadata:
  version: "1.0"
  origin: "original-kit-skill"
---

# Effects must have a readable job

Write a one-sentence purpose: show tension, reveal a layer, communicate softness, or focus attention. Compare the plain material. Remove the shader if it obscures the product or makes text harder to read.

## Build steps
1. Prototype one effect on a simple mesh, with named uniforms and bounded ranges. Start with static output; then add user-controlled progress.
2. Track spaces explicitly: local, world, view, clip, tangent. Define color space for every input and tone mapping/output conversion exactly once.
3. Displacement that changes silhouette may require geometry bounds, shadows and normals to change; fragment-only distortion does not create physical geometry.
4. Declare whether glass is alpha blending, screen-space refraction, transmission or a fuller optical approximation. Screen-space effects cannot see offscreen or occluded content magically.
5. Budget transparent overdraw, render targets and passes. Multiple overlapping transmission objects can be much more expensive than a simple opaque mesh.
6. Test extensions/precision and shader compilation on the actual browser/renderer path. Do not mix WebGL shader snippets into a WebGPU/TSL graph without a translation plan.
7. Provide a plain material fallback and reduced-motion path. Expose progress to the same story controller; do not add a second clock hidden inside the shader.

## Gate
No unexplained NaNs, flashing or per-frame allocations. Text remains DOM text. A screenshot proves one frame, not correct behavior at every parameter extreme.

Sources: R08, R09. See `resources/MATERIALS-AND-EXPORT.md` for the explicit limits of this kit's tiny preview shader.

## Kit location
Kit root: `{{KIT_ROOT}}`. The sync script expands this token. In the canonical ZIP, resolve the root two directories above this skill folder. Paths mentioned above are relative to that root. Read only the referenced files needed for the task.
