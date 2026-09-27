---
name: pd-remotion-production
description: "Create frame-deterministic video compositions, product films, explainers and journey derivatives with Remotion."
license: MIT (original guidance; linked tools and assets keep their own licenses)
---

# Remotion Production

Read the current official Remotion skills as optional upstream guidance; keep their acquisition/license record and do not assume the framework is MIT or universally free. Align Remotion packages to one tested version in the lockfile. Separate composition source, asset preparation, rendering and publishing.

Express time as frame-derived state. A renderer may evaluate frames out of order; avoid wall-clock timers, uncontrolled randomness, global mutable state and browser-only animation progress. Derive dimensions, durations and input types before rendering. Use real measured source dimensions for crop/contain/zoom mapping, and keep source-space overlays on the same transform as their media.

Use isolated local staging and content-hashed asset names. The included guarded overlay replaces unsafe PR87 staging and shell execution, but its complete Remotion runtime remains an on-device qualification task. Bundle immutable source for reuse in production; the one-run canary bundling path intentionally favors isolation over throughput.

Render boundary/key frames, then the entire deliverable. Decode the output and verify dimensions, duration, framerate, audio, captions, aspect variants and loop/end behavior. Inspect typography and crops visually. An MP4 is not an interactive page; a video annotated from a journey is presentation media, not a replacement for its immutable capture and assertion records.

## Related contracts

Read the repository's `docs/visual-production/E2E-CONTRACT.md`, `ALL-FORMS.md`, and source catalog for the selected tool. In the standalone kit these are under `docs/` and `resources/`. Preserve exact failure/blocked states and the existing source/evidence owners.
