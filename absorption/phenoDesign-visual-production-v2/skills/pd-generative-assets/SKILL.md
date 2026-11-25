---
name: pd-generative-assets
description: "Source or locally generate raster, texture and 3D candidates without confusing generation with production readiness."
license: MIT (original guidance; linked tools and assets keep their own licenses)
---

# Generative Assets

Choose procedural construction, stock/licensed assets, photography/scanning or model generation based on the need. Do not assume a generative model is the cheapest route to accurate geometry, typography or repeatable product details. Compare at least one non-generative alternative against quality and repair effort.

For local workflows, record model/checkpoint hashes, code revision, sampler/configuration, seed, input permissions, licenses and dependencies. Tool licenses do not automatically cover model weights or source images. New custom nodes/plugins are executable software: inspect and isolate them before giving filesystem or network access. Hosted services are not local execution and may upload private assets; require the appropriate approval.

Treat generated meshes and images as candidates. Repair silhouettes, material continuity, topology, normals, UVs, seams, anatomy, repeated details and text. Retopologize or rebuild when the result cannot meet runtime and editability constraints. Preserve an editable production source and useful intermediate steps, not only the final flattened image.

Verify export and actual consumer rendering. Label concepts/synthetic scenes, retain reference rights, and do not generate or retouch screenshots to manufacture evidence. Agent autonomy means performing this repair/validation loop, not merely submitting a prompt and declaring the asset complete.

## Related contracts

Read the repository's `docs/visual-production/E2E-CONTRACT.md`, `ALL-FORMS.md`, and source catalog for the selected tool. In the standalone kit these are under `docs/` and `resources/`. Preserve exact failure/blocked states and the existing source/evidence owners.
