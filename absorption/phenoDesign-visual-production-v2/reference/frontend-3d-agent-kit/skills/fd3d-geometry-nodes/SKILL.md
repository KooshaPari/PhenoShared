---
name: fd3d-geometry-nodes
description: "Build parameterized Blender Geometry Nodes props, scatter, patterns and repeatable mechanisms; use for editable variations rather than one-off destructive modeling."
license: MIT
metadata:
  version: "1.0"
  origin: "original-kit-skill"
---

# Geometry Nodes as a source asset

Begin with a Python or manual blockout to establish proportions. Use Geometry Nodes when the user will actually benefit from parameterized changes, distributions or repeatable structure.

## Node-group contract
Expose a small meaningful interface: size, spacing, count, radius, seed, profile and detail tier. Units and min/max ranges must be explicit. Name sockets and the node group semantically; probe the installed Blender API rather than copying obsolete interface calls.

## Pattern recipe
For an interactive dial: curve circle → resample by count → points → instance a beveled knurl segment → align to tangent/radial direction → realize instances only at the delivery boundary. Keep a separate central body and glass lens. Derive seed from the asset identity, not wall-clock time.

For textile/repetition: use source instances in the editable file and bake appearance when microgeometry is below screen-pixel size. A thousand physical stitches across a hero may add cost with no visible benefit.

## Evaluation loop
Vary minimum, nominal and maximum inputs. Check bounding box, part count, non-finite geometry, collisions and render quality. Preserve an editable node version and a evaluated low-poly export. Retain rest transforms and part IDs after realizing instances.

## Gate
No missing external node group, local-only dependency or hidden texture. No unbounded count slider. The export must be tested after applying/evaluating modifiers. A node graph screenshot is documentation, not proof the graph works.

Sources: R05, R06. See `resources/BLENDER-AUTONOMY.md`. This kit describes the node workflow; it does not claim to include a version-tested Geometry Nodes implementation.

## Kit location
Kit root: `{{KIT_ROOT}}`. The sync script expands this token. In the canonical ZIP, resolve the root two directories above this skill folder. Paths mentioned above are relative to that root. Read only the referenced files needed for the task.
