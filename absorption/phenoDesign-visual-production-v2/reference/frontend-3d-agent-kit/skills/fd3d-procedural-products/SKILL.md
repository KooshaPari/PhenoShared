---
name: fd3d-procedural-products
description: "Model original product props such as sneakers, headphones, bottles, keyboards and controls from parameters; use when editable local geometry is preferable to generated black-box meshes."
license: MIT
metadata:
  version: "1.0"
  origin: "original-kit-skill"
---

# Procedural product modeling

## Establish the shape contract
Record bounding ratios, primary silhouette, positive/negative spaces, functional components, material boundaries and the close-up distance. A shoe needs an opening, toe volume, heel structure, tongue and laces; a rounded blob with a stripe is not enough.

## Build in passes
1. Block the overall envelope with low-cost lofts, lathed profiles, curves or beveled primitives. Keep a neutral clay material and fixed camera.
2. Compare front/profile/three-quarter silhouettes. Reject the blockout when recognizability depends on a logo.
3. Separate functional parts at real construction seams. Preserve a rest transform and one stable node name per animatable component.
4. Add characteristic secondary forms: collar, tongue, welt, sole layers and support cage for a trainer; gasket, knurl and lens for a dial.
5. Use curves/tubes for cables, laces and seams; arrays/instances for repeats. Keep source parameters instead of destructive repetition.
6. Add bevels proportional to object scale. Test highlights, not just wireframe. Do not use excessive subdivisions to compensate for bad proportions.
7. Audit self-intersections, open boundaries, normals, shading and material assignment. Overlapping constructive meshes may be acceptable for a distant concept but must be disclosed and resolved for close-ups or manufacturing.
8. Keep high and low versions separate, derive delivery geometry from source and verify named-part semantics survive optimization.

## Starting implementation
`scripts/build_asset.py` is a standard-library original trainer generator, producing JSON + GLB + browser data. It is a concept seed with no UVs, not a scan or production footwear model. Rebuild through `blender/build_product.py` for an editable native scene.

## Gate
The form passes at least three views in clay. Fix form before adding particles, bloom, brand graphics or a complex shader.

Sources: R05, R06, R08. See `recipes/sneaker-story.md`.

## Kit location
Kit root: `{{KIT_ROOT}}`. The sync script expands this token. In the canonical ZIP, resolve the root two directories above this skill folder. Paths mentioned above are relative to that root. Read only the referenced files needed for the task.
