---
name: fd3d-gltf-delivery
description: "Export Blender or procedural assets to compact GLB/glTF with intact part names, materials and interaction semantics; use before shipping 3D to a browser."
license: MIT
metadata:
  version: "1.0"
  origin: "original-kit-skill"
---

# Asset delivery is a semantic boundary

## Procedure
1. Record source identity, units, axes, bounds, rest transforms and named animatable parts. Export only delivery geometry, not the studio floor or hidden reference objects.
2. Check glTF material/extension support in the target loader. Bake unsupported procedural node effects. A Blender shader graph is not serialized wholesale into GLB.
3. Export an unoptimized reference. Validate with the Khronos validator and load in an independent viewer, then in the actual application.
4. Measure geometry, compressed network bytes, decoded texture memory, primitive/material count and draw calls. Small file size does not imply small GPU memory.
5. Optimize one stage at a time. Compare before/after image and semantic inventory. Joining, flattening or pruning can destroy parts required for exploded views and hotspots.
6. Evaluate Meshopt/Draco and KTX2 only with the corresponding decoder/transcoder integrated and cache paths tested. Compression can move cost into CPU startup and shader preparation.
7. Include a properly framed poster, mobile/lower-detail option and rights manifest. Avoid a hardcoded canvas-sized texture for every icon or panel.

## Included checker boundary
`scripts/audit_asset.py` checks this kit's own GLB container, accessors, indices, names and hashes. It is deliberately NOT a full Khronos validator or proof that any arbitrary glTF renders correctly.

## Gate
All required node names survive. Exported material appearance is reviewed. Missing decoder, texture, source or license is a failed delivery, even when a single development machine happens to load it from cache.

Sources: R06, R08, R16, R17, R18. See `resources/MATERIALS-AND-EXPORT.md`.

## Kit location
Kit root: `{{KIT_ROOT}}`. The sync script expands this token. In the canonical ZIP, resolve the root two directories above this skill folder. Paths mentioned above are relative to that root. Read only the referenced files needed for the task.
