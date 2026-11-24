---
name: fd3d-blender-autonomy
description: "Create and revise editable 3D assets locally through headless Blender Python, with optional isolated MCP; use for autonomous modeling, rendering and export."
license: MIT
metadata:
  version: "1.0"
  origin: "original-kit-skill"
---

# Autonomous Blender is a feedback loop

## Input
An asset brief with dimensions or ratios, named parts, source rights, intended browser placement, render budget, output directory and required views.

## Procedure
1. Run `scripts/doctor.py`. Identify the actual executable and installed version. A reported application on another device is not an available worker.
2. Work in a new background process and owned job directory. Default to `scripts/run_blender.py` dry-run. Only add `--run` after inspecting the command and source.
3. Parameterize the model in a committed Python recipe. Store units, axes, origin and functional part names. Do not let an unsaved GUI session become the only source.
4. Build a cheap silhouette pass. Render profile, three-quarter and rear/top views. Inspect the actual pixels before increasing geometry or texture resolution.
5. Fix silhouette and proportions first, intersections/normals second, materials and lighting third. Change a small set of parameters between comparisons.
6. Preserve `.blend`, generator, input data and version receipt. Export a GLB and reload it independently. Native Blender beauty does not prove exported material fidelity.
7. Compare the browser's initial frame and key story frames with the intended art direction. Store failures and rerun exact outputs after edits.

## MCP is optional
Use a reviewed, pinned local bridge only when interactive scene inspection is worth a persistent editor. The Blender Lab MCP and ahujasid/blender-mcp are different projects. The community bridge can run arbitrary Python; online generation integrations are not an offline local workflow. Disable its telemetry, minimize credentials and use OS isolation. An instruction file or a "safe mode" label is not a sandbox.

## Deliver / stop conditions
Native project, source recipe, export, three previews and receipt. Missing Blender means BLOCKED_ENV, not a fake `.blend` or a success claim. Never delete the operator's existing scene or steal focus from foreground work.

Sources: R05, R06, R07, R24. See `blender/build_product.py` and `resources/BLENDER-AUTONOMY.md`.

## Kit location
Kit root: `{{KIT_ROOT}}`. The sync script expands this token. In the canonical ZIP, resolve the root two directories above this skill folder. Paths mentioned above are relative to that root. Read only the referenced files needed for the task.
