---
name: pd-material-textures
description: "Create materials, texture sets and 2.5D surfaces consistently across raster sources, Blender and realtime consumers."
license: MIT (original guidance; linked tools and assets keep their own licenses)
---

# Material Textures

Name the physical or stylized material target and collect rights-cleared references under controlled lighting. Separate base color, roughness, metallic/specular behavior, normals, displacement, opacity and emission. A convincing beauty render is not evidence that all texture channels are correct.

Author editable procedural graphs, layered texture sources or both. Keep real-world scale and UV density explicit. Compare a neutral material ball/flat patch and the actual object; a shader may look good on a sphere but fail on a thin product edge. For glass, specify thickness, background dependence, highlights and acceptable realtime approximation.

Export channels with explicit color-space and packing conventions. Never apply an sRGB transform to data maps merely because the images look dark in a viewer. Document normal orientation and tangent basis, premultiplied/straight alpha and compression decisions. Preserve a nontransparent fallback where layered transmission is too expensive.

Validate texture seams, mip/normal artifacts, magnification, grazing highlights, light/dark backgrounds and mobile renderer differences. Measure transfer and memory independently from file size. Material graphs that cannot transfer directly should bake or use a reviewed target-runtime recreation, with a retained visual comparison and known limitations.

## Related contracts

Read the repository's `docs/visual-production/E2E-CONTRACT.md`, `ALL-FORMS.md`, and source catalog for the selected tool. In the standalone kit these are under `docs/` and `resources/`. Preserve exact failure/blocked states and the existing source/evidence owners.
