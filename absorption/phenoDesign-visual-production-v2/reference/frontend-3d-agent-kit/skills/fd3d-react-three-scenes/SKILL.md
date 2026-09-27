---
name: fd3d-react-three-scenes
description: "Structure React Three Fiber scenes with stable ownership, GLB loading, reusable resources and on-demand rendering; use when the frontend already uses React."
license: MIT
metadata:
  version: "1.0"
  origin: "original-kit-skill"
---

# React owns structure; the frame loop owns transient pose

## Architecture
Use one Canvas for a cohesive stage. Put semantic content and controls outside it. Keep asset loading/error boundaries, a stable scene root, named part map, camera and light rig explicit. Initialize rest transforms once after asset readiness.

## Working rules
- Use refs for high-frequency transforms. Do not call React setState at display frequency just to rotate a group.
- Select one render policy: on-demand with explicit invalidation, or a bounded active loop. Demand rendering needs a short continuation while springs settle, not an unconditional endless invalidate.
- Reuse geometry/materials/textures deliberately. Cached GLTF scenes can share resources; cloning a scene does not always clone materials. Clone a material before per-instance edits when another consumer shares it.
- Dispose owned resources at unmount. Do not dispose shared cache resources while other instances still need them.
- Move scroll/control ownership outside individual parts. Store rest transforms, then compute absolute offsets. Keep hooks and lifecycle cleanup correct under development remounts.
- Bound DPR and adapt by measured frame cost, not user-agent labels. A desktop browser can be on a busy integrated GPU.
- Stage loading: poster first, model when useful, expensive effects after capability/interaction. Avoid a giant Suspense boundary hiding the entire page.

## Verification
Test mount→unmount→remount, route changes, WebGL loss, material variants and two instances. Record console errors and draw/resource counters. An empty scene plus a green React build does not pass.

Sources: R08, R09. The included Three/GSAP adapter is plain JS, not a tested React application. Port deliberately rather than pretending framework choice changes asset quality.

## Kit location
Kit root: `{{KIT_ROOT}}`. The sync script expands this token. In the canonical ZIP, resolve the root two directories above this skill folder. Paths mentioned above are relative to that root. Read only the referenced files needed for the task.
