---
name: pd-spatial-scenes
description: "Plan AR/XR and richer spatial presentations while preserving source, scale, material and interaction semantics."
license: MIT (original guidance; linked tools and assets keep their own licenses)
---

# Spatial Scenes

Treat spatial delivery as an extension of the product story, not a compulsory upgrade from 3D. Specify physical scale, origin, handedness, camera/navigation model, lighting assumptions and collision/selection behavior. Determine whether a simple web viewer would satisfy the need before accepting device/runtime complexity.

Use suitable source/interchange formats deliberately. Preserve a full editable scene while delivering optimized runtime geometry. OpenUSD composition, Blender scenes and glTF/GLB exports have different roles; a successful conversion does not prove equivalent materials, animation or instancing. Validate units and dimensions with a known-size reference.

Keep instructions readable and controls reachable across pointer, keyboard, touch and the actual spatial device's input model. Provide a non-XR route for essential content. Avoid forced motion and maintain a clear exit/reset path. Test tracking loss, session interruption and resource disposal.

Acceptance requires deployment to the intended renderer/device, input and scale checks, real captures, material/lighting review and a fallback journey. Do not label a desktop screenshot as headset/AR evidence. Reuse existing graphics/runtime owners and only qualify device-specific capabilities that were actually exercised.

## Related contracts

Read the repository's `docs/visual-production/E2E-CONTRACT.md`, `ALL-FORMS.md`, and source catalog for the selected tool. In the standalone kit these are under `docs/` and `resources/`. Preserve exact failure/blocked states and the existing source/evidence owners.
