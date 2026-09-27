---
name: pd-after-effects-production
description: "Use After Effects for editable motion design and compositing with controlled native authoring and aerender delivery."
license: MIT (original guidance; linked tools and assets keep their own licenses)
---

# After Effects Production

Use AE when its compositing, timeline/effects or artist handoff are needed; do not add it to a simple deterministic title card that Remotion or FFmpeg already handles. Probe host/version, effects, fonts and licensing. Author .aep in a dedicated session, then use a qualified aerender invocation for renders. Headless rendering does not imply that arbitrary authoring and plugin setup are headless.

Build comps at explicit dimensions, pixel aspect, color settings and frame rates. Keep expressions deterministic and collect linked sources without copying unlicensed fonts. Name layers and controls. Parameterize useful variation; preserve a baseline composition and render settings rather than modifying the only source for each output.

The supplied canary creates a simple editable comp and stops before claiming a native render. Extend it only through installed-version API checks. Native app automation must never save over or close unrelated operator projects.

Acceptance includes cold reopen, missing-footage/plugin/font checks, deterministic sampled frames, full output decode, alpha/profile checks, source-to-export timing and downstream playback. Test one intentionally broken dependency to ensure the automation fails visibly instead of rendering a substitute. Export consumer variants from a retained master, with time edits explicitly described.

## Related contracts

Read the repository's `docs/visual-production/E2E-CONTRACT.md`, `ALL-FORMS.md`, and source catalog for the selected tool. In the standalone kit these are under `docs/` and `resources/`. Preserve exact failure/blocked states and the existing source/evidence owners.
