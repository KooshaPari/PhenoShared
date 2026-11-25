---
name: pd-remotion-regressions
description: "Test Remotion asset staging, crop geometry, timeline boundaries, cancellation and actual encoded media."
license: MIT (original guidance; linked tools and assets keep their own licenses)
---

# Remotion Regressions

Challenge a render pipeline with adversarial but legitimate inputs before adding more templates. Test two source files with the same basename but different bytes, two concurrent jobs, paths outside the authorized root, symlinked inputs, malformed dimensions, missing durations and invalid annotations. No input should delete shared staging or invoke a shell command.

Use source images with distinct corner/center markers and aspect ratios different from the output. Test cover and contain, both ends of zoom, crop offsets and source-space highlights. Keep scene-local time distinct from full-composition duration. At an annotation's end frame it must disappear; a click ripple must not repeat forever unless repetition was requested.

Verify source dimensions using metadata, not the intended output width. Render deterministic boundary frames and full audio/video with installed pinned dependencies. Decode the final file and compare streams, duration and resolution. Test missing browser/tool packages as blocked conditions instead of allowing implicit network installation.

The included pure-function tests are regression evidence for those functions only. They do not exercise React, Remotion's browser, native GPU output or the real viewer/recorder. Keep those remaining lanes visible and do not merge solely because the dependency-free test suite is green.

## Related contracts

Read the repository's `docs/visual-production/E2E-CONTRACT.md`, `ALL-FORMS.md`, and source catalog for the selected tool. In the standalone kit these are under `docs/` and `resources/`. Preserve exact failure/blocked states and the existing source/evidence owners.
