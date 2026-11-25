# Materials, lighting and browser export

## A material family, not a list of shiny colors

Use physical differences as the system: cloth with broad soft response; rubber with dense dark diffuse form; satin metal with directional/wider highlights; polished metal with sharper reflected structure; ceramic with a hard body and distinct glaze; clear, smoked and frosted glass with different transmission/roughness/absorption intent; resin with body color and appropriate translucency.

For each material record base color, roughness, metalness, normal/microstructure scale, transmission intent, thickness and target renderer. These are parameters to art-direct and measure, not universal constants. The kit does not claim spectral optics, real subsurface fidelity or glass parity across engines.

## Practical export boundary

Authoring shader graphs contain effects that GLB cannot necessarily represent. Use supported glTF material models/extensions and test the exact loader. Bake required procedural surfaces to maps; retain the native graph. Declare which details are native-only and which are delivered. Do not send an unbaked procedural node graph and call the browser's flat material "equivalent".

Color/base-color and data maps need distinct color-space handling. Keep roughness/metalness/normal maps as data and apply the renderer's required color treatment for color textures. Record channel packing. Inspect normal-map convention in the actual renderer, including mirrored UVs and seams. Do not hide doubled tone mapping in a screenshot comparison.

Glass can require thickness, an environment and extra render passes. Alpha alone is not refraction. Screen-space refraction only sees available screen-space information. CSS `backdrop-filter` is useful interface glass, not a replacement for a modeled optical object. It can be used alongside 3D, but keep the semantics honest.

## Optimization with semantic constraints

Begin with an uncompressed reference asset. Identify required names and rest transforms. Then run independent optimization experiments: simplify geometry, reduce/atlas textures, consolidate genuinely static materials, choose compression, and test decoder loading. Never use a blanket join/flatten command when separate `Upper`, `Midsole`, `Outsole`, dial/lens or hinge nodes are needed.

Measure network bytes separately from decoded memory. A 2048² RGBA texture is about 16 MiB before mip levels in an uncompressed representation; compressed transfer size does not remove that runtime budget. Actual GPU texture formats and transcoding determine device storage. Keep claims tied to the target backend.

## Included model limitations

The concept trainer is generated from lofts, tubes and ellipsoids. It has no UVs/textures in its canonical GLB, overlapping constructive surfaces, stylized proportions and no manufacturing-ready topology. It is intended for editing and workflow demonstration. Its original structured source, generator, GLB, named components and export hashes are included. The browser shader uses simple lighting with procedural visual hints; the CPU fallback approximates triangle lighting and depth ordering. Neither proves a finished production material.

Sources: R06/R08/R16/R17/R19/R36. Use `contracts/asset.schema.json` as a minimum interface, not an assertion of complete industry metadata.
