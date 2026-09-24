# Provenance: eyetracker

## Source

- **Repository:** [<REDACTED>/zz-merge-unk-eyetracker](https://github.com/KooshaPari/zz-merge-unk-eyetracker)
- **Absorbed:** 2026-09-15
- **License:** MIT (see LICENSE in source repo)

## Crates Migrated

| Crate | Description |
|-------|-------------|
| `eyetracker-domain` | Domain types and errors |
| `eyetracker-math` | Math utilities for eye tracking |
| `eyetracker-core` | Core tracking algorithms |
| `eyetracker-camera` | Webcam capture module |
| `eyetracker-inference` | ML inference pipeline |
| `eyetracker-cli` | CLI application |
| `eyetracker-ffi` | UniFFI bindings for cross-platform use |

## Notes

- Source repo is preserved as-is (not deleted or archived).
- All inter-crate path dependencies retained as `path = "../eyetracker-*"`.
- `eyetracker-math` dev-dependency `criterion` now uses `workspace = true`, resolving to the workspace's `0.5` (root `Cargo.toml`); unchanged from the source repo's `0.5`. Corrected 2026-09-24 — the previous claim ("workspace version 0.8") was false.
- `eyetracker-cli` fixes (pre-existing bugs in source repo):
  - Added missing `core_graphics` imports (`CGEventSource`, `CGEventSourceStateID` from `event_source` module; `CGEventType` at module level).
  - Enabled `highsierra` feature on `core-graphics` dep for `new_scroll_event`.
  - Fixed `new_scroll_event` return type from `Option` to `Result` (core-graphics 0.23 API).
