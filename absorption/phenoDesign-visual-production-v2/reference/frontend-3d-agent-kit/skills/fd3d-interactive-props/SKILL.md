---
name: fd3d-interactive-props
description: "Build active interface props such as dials, hinged devices, material selectors, magnetic controls and animated vector states; use when the object must respond meaningfully to input."
license: MIT
metadata:
  version: "1.0"
  origin: "original-kit-skill"
---

# Props are interfaces, not unattended screensavers

Define a small state machine before physics: idle, focused, dragging, activated, settling, disabled. Map each transition to real input and an observable result. Keep a semantic DOM control as the source of truth.

## Examples
- Material swatch: a real button/radio updates the same named material and announces its selected state. It works before model load.
- Knob/dial: a range input owns a bounded value; pointer/keyboard update that value; the 3D dial merely visualizes it. Page scrolling must still work on touch.
- Hinged product: a button toggles open/closed, moves a pivoted child and reveals corresponding DOM content. Do not animate around the mesh origin when it is not the hinge.
- Active vector illustration: a Rive/SVG state machine reflects loading/success/error, with text equivalents. Avoid implying it is live system evidence when it is decorative.
- Physical toy: use a physics engine only when collisions/manipulation are the point. Suspend or isolate simulation while scroll choreography owns the same body.

## Procedure
Determine pointer capture policy, cancel behavior, bounds, keyboard equivalents and reset. Hit targets are DOM-sized, not tiny projected mesh triangles. Keep focus visible and never put required instructions only inside a texture. Test rapid interactions and cross-input transitions, not just the happy-path demo recording.

## Gate
One input has one predictable effect. The user can interrupt and reverse movement. No forced motion or audio. Data values do not change from decorative spring oscillation. State remains correct if the renderer fails.

Sources: R14, R15, R21. See `recipes/glass-control.md` and `recipes/active-props.md`.

## Kit location
Kit root: `{{KIT_ROOT}}`. The sync script expands this token. In the canonical ZIP, resolve the root two directories above this skill folder. Paths mentioned above are relative to that root. Read only the referenced files needed for the task.
