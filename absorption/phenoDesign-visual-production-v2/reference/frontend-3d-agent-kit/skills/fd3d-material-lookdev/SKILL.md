---
name: fd3d-material-lookdev
description: "Create coherent physical materials, including frosted/smoked glass, resin, ceramics, textile and metal; use for Blender look development and browser material translation."
license: MIT
metadata:
  version: "1.0"
  origin: "original-kit-skill"
---

# Materials: substance before gloss

## Input
Material role, thickness, intended lighting, surface scale, target renderer and export requirements. A color name alone is not a material brief.

## Procedure
1. Separate base color from lighting, roughness from metalness, and opacity from transmission. Do not call every shiny surface metallic.
2. Use a neutral three-point or studio environment to compare material candidates. Lock exposure and camera while changing one material variable.
3. Make a bounded family: polished/satin metal; matte/glazed ceramic; clear/smoked/frosted glass; soft/hard resin; textile/rubber. Give each distinct roughness, highlight width, edge behavior and microstructure.
4. Glass needs meaningful thickness, a believable surrounding environment and a readable silhouette. CSS backdrop blur is an interface effect, not physical volume refraction. Browser transmission is often a costly approximation, not spectral optics.
5. Use UVs and texture density appropriate to closest camera distance. Keep albedo/base color separate from normal, roughness and occlusion. Avoid baking dramatic lighting into base color.
6. Bake procedural Blender inputs required by the browser. Inspect channels and normal orientation. Keep colorspace treatment explicit for color versus data textures.
7. Compare material swatches in Blender, exported GLB and browser. Record intentional differences in tone mapping or missing extensions.

## Gate
The product is readable without bloom. Transparent surfaces remain usable over real page content. Material controls change a named material consistently, not every mesh by accident. The kit's CPU preview and tiny WebGL shader are inspection renderers, not evidence of production PBR or glass fidelity.

Sources: R06, R08, R19, R20. See `recipes/glass-control.md` and `resources/MATERIALS-AND-EXPORT.md`.

## Kit location
Kit root: `{{KIT_ROOT}}`. The sync script expands this token. In the canonical ZIP, resolve the root two directories above this skill folder. Paths mentioned above are relative to that root. Read only the referenced files needed for the task.
