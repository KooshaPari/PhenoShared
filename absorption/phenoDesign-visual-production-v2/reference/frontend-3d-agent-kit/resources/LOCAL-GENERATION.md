# Optional local image-to-3D: qualified, not mandatory

The most dependable default for parameterized product props is ordinary local modeling. Generation is a second lane for exploration. It must not be silently substituted with a hosted API.

## Hunyuan3D-2.1 (R23)

The reviewed upstream README gives different VRAM needs for shape (10 GB), texture (21 GB), and combined processing (29 GB). Those are upstream stated requirements, not a guarantee of success with the rest of the user's workload running. Its toolchain/dependencies and code/model terms require inspection. Platform labels do not establish Apple Metal acceleration for each component. Try stages separately only where the actual implementation supports it; measure peak rather than adding optimistic estimates.

## TRELLIS.2 (R24/R35)

The primary model card reports Linux testing and NVIDIA GPUs with at least 24 GB. Treat that as a starting compatibility boundary, not an assurance that an arbitrary 24 GB GPU has sufficient free memory or that macOS/CUDA alternatives work. Inspect the exact model/code/dependency licenses and revision. Avoid unsupported precision/offload patches being represented as an officially supported path.

## A usable generated-asset pipeline

Approve input rights and local download size → pin environment/weights → generate raw candidates → inspect every view → remove fragments/fix topology → retopologize as necessary → UV and bake → split functional parts and set pivots → create appropriate LODs → validate export and browser → retain source/candidate/cleanup history.

An image generator can hallucinate unseen geometry, openings, laces or material structure. A plausible texture can conceal unusable mesh structure. A raw object usually has no knowledge of the semantic pieces required by an exploded product story. Record these as cleanup tasks, not as a mysterious failure of the frontend engine.

## Before running anything

The agent must show exact selected repo/commit/model, supported hardware/backend, expected disk/VRAM, license/rights status and whether any data leaves the machine. The user approves installation/download/external spend separately. Use a dedicated environment, not the frontend repo's Python/Node dependency tree. This ZIP contains no weights, local-generation installer or remote service credentials.

Prefer a measured procedural/source-asset route over a model download when the task is a simple dial, container, keyboard, logo, frame or regular hard-surface prop. The question is time to a good editable result, not novelty of the first generated mesh.
