---
name: fd3d-local-generative-3d
description: "Evaluate optional on-device image-to-3D models, hardware fit, licensing and cleanup; use only when procedural or licensed source assets are insufficient."
license: MIT
metadata:
  version: "1.0"
  origin: "original-kit-skill"
---

# Generation is a proposal, not the production asset

## Choose the route
Try procedural modeling for regular products and a rights-cleared source model for exact commercial products. Use image-to-3D when organic/ambiguous form exploration justifies a model install and cleanup. Do not imply text-only generation understands hidden manufacturing details.

## Qualify before download
Record model repo/revision, code license, weight license, input rights, backend, driver/toolchain, disk and peak VRAM requirement. Hunyuan3D-2.1's published shape/texture/combined requirements differ; TRELLIS.2's reference requirements are Linux/NVIDIA-centric. A macOS listing does not prove an accelerated Metal pipeline or workable memory budget.

Downloads, paid APIs and upload of user assets require explicit approval. A Blender MCP feature calling a hosted generator is not on-device generation. Keep local generation in its own environment; do not contaminate the production frontend's dependency tree with CUDA wheels or compiler toolchains.

## Post-generation work
Inspect all views, open boundaries, inner/underside geometry, duplicated texture features and disconnected fragments. Repair/retopologize, UV/bake, separate semantic parts, place pivots and create LODs. Test whether the generated texture merely hides bad geometry. Evaluate source-image resemblance without making unsupported claims about exact dimensions.

## Gate
A named-part exploded view cannot be obtained reliably by treating an opaque generated mesh as already structured. Preserve the raw candidate and a reproducible cleanup recipe. Mark non-reproducibility and any unresolved commercial-use rights.

Sources: R23, R24, R07. See `resources/LOCAL-GENERATION.md`.

## Kit location
Kit root: `{{KIT_ROOT}}`. The sync script expands this token. In the canonical ZIP, resolve the root two directories above this skill folder. Paths mentioned above are relative to that root. Read only the referenced files needed for the task.
