---
name: pd-rive-authoring
description: "Use the current Rive CLI and source workflow for locally authored interactive vector assets and state machines."
license: MIT (original guidance; linked tools and assets keep their own licenses)
---

# Rive Authoring

Qualify the installed Rive CLI through --help and official CLI/agent documentation before choosing the path. The reviewed September 2026 docs describe code-first RML scene authoring, inspection, verification and screenshots. Record the actual installed capability set; do not reuse the outdated blanket claim that Rive is editor-only.

Let the CLI generate its project scaffolding and agent instructions. Read local schema/docs, define named artboards and input/data contracts, then build the vector/rig/state machine in small verified increments. Preserve RML/project inputs and any generated editor source alongside the runtime .riv export. CLI/editor round-trip limitations must be recorded rather than assumed away.

State transitions should have explicit interruption and recovery behavior. Test rapid input, pointer exit, focus loss, reduced motion, disabled states and missing assets. Expose essential operations through DOM controls or native accessibility semantics rather than hiding all meaning inside a canvas.

Run the qualified CLI verification and capture paths, then test the exported .riv in the actual web/native consumer with its selected runtime version. Report source verification, runtime playback and perceptual review separately. Prefer SVG/CSS for a small non-rigged interaction where Rive's runtime and authoring dependency do not earn their cost.

## Related contracts

Read the repository's `docs/visual-production/E2E-CONTRACT.md`, `ALL-FORMS.md`, and source catalog for the selected tool. In the standalone kit these are under `docs/` and `resources/`. Preserve exact failure/blocked states and the existing source/evidence owners.
