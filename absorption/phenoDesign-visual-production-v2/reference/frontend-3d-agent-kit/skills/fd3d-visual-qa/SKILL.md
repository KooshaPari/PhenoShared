---
name: fd3d-visual-qa
description: "Run render-inspect-revise loops and browser interaction checks for generated frontend/3D; use to turn code completion into evidence-backed design delivery."
license: MIT
metadata:
  version: "1.0"
  origin: "original-kit-skill"
---

# Visual iteration must actually see the output

## Evidence loop
1. Establish a fixed scene/viewport/camera seed and one concrete hypothesis: silhouette is wrong, lighting hides the surface, or motion is too busy. Keep other variables stable.
2. Render three model views and five story progress checkpoints. Include mobile, low-motion and fallback states.
3. Inspect the pixels. List visible defects with frame and region; separate geometry, material, composition, copy, interaction and technical failure.
4. Make a small targeted revision. Re-render the same views, compare against the prior candidate and retain the rejected result when it explains a decision.
5. Test actual user actions with Playwright or an equivalent harness: scroll forward/back, chapter jump, material change, separate/rejoin, keyboard rotate, pause, resize, route lifecycle and renderer failure.
6. Keep logs, screenshots, source/export hashes and exact environment. A screenshot from a CPU approximation does not certify the WebGL shader; a mock cannot prove pixels.
7. Report PASS, FAIL, BLOCKED_ENV or NOT_RUN separately per capability. A script's successful exit is not aesthetic approval.

## Acceptance
Use `resources/QUALITY-GATES.md`, not a single subjective model-generated score. Explain what a simpler alternative did better. Do not enhance test screenshots to hide defects or invent FPS/byte measurements. Ask for human art approval when the brief requires it; continue all executable checks rather than stopping at a vague need for review.

Sources: R22, R17, R18. See `evidence/` and `tests/` for this kit's explicit verification boundary.

## Kit location
Kit root: `{{KIT_ROOT}}`. The sync script expands this token. In the canonical ZIP, resolve the root two directories above this skill folder. Paths mentioned above are relative to that root. Read only the referenced files needed for the task.
