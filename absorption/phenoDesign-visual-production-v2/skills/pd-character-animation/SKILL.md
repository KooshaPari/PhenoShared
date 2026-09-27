---
name: pd-character-animation
description: "Create expressive 2D or 3D characters and mascots with coherent construction, rigs and state behavior."
license: MIT (original guidance; linked tools and assets keep their own licenses)
---

# Character Animation

A character is an authored design, not a circle with random eyes added by the UI implementation. Start with a character bible: silhouette, proportions, material/line grammar, personality boundaries, expression range and forbidden deformations. Establish front, side and three-quarter references with consistent features.

Choose a medium deliberately: frame animation for drawn performance, Rive/rigged vector for responsive expressions, or Blender for volume and changing cameras. Keep named layers or meshes separable for rigging. Define pivots, constraints, neutral/rest pose, expression controls and a bounded state graph such as idle, attend, anticipate, act, succeed, fail and recover.

Author timing with anticipation, clear poses and purposeful secondary motion. Do not loop a distracting idle forever. User input may redirect attention; it must not create an unsettling or blocking assistant mascot. Low motion and no-animation modes must retain all product functionality.

Validate joint extremes, eye and mouth consistency, silhouette at target size, transition interruption, simultaneous inputs and lifecycle cleanup. Compare holds and transitions, not just a contact sheet of good poses. Source files, rig controls, export settings and captured runtime sequences must be preserved. Critique whether this feels like a designed character before optimizing its draw calls.

## Related contracts

Read the repository's `docs/visual-production/E2E-CONTRACT.md`, `ALL-FORMS.md`, and source catalog for the selected tool. In the standalone kit these are under `docs/` and `resources/`. Preserve exact failure/blocked states and the existing source/evidence owners.
