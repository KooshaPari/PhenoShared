# ADR-0006: absorb `agileplus-spec-harmonizer` (+ duplicate `-tool`) into the `AgilePlus` workspace

**Status:** Accepted
**Date:** 2026-06-18
**Deciders:** KP, code review

## Context

Two sibling repos exist for spec-format ingestion:

- `<REDACTED>/agileplus-spec-harmonizer` (Public, Rust) — "Harmonizer for GSD,
  OpenSpec, BMAD-Method, and Spec-Kitty spec formats → unified WorkPackage shape.
  12/12 tests pass. Pure Rust, no async, no cgo."
- `<REDACTED>/agileplus-spec-harmonizer-tool` (Public, Rust) — "Preserved local WIP
  from agileplus-spec-harmonizer-tool."

User directive: absorb both repos into `AgilePlus` + `agent-platform`.

## Decision

**Absorb both repos into `AgilePlus` as a new workspace crate. Do NOT route any
of the content into `agent-platform`.**

### What was migrated

- 5 source files (`lib.rs`, `parsers/{mod,gsd,openspec,bmad,kitty}.rs`,
  `normalize.rs`, `emit.rs`) — total ~600 LoC
- 1 integration test (`tests/integration.rs`)
- 1 fixture (`fixtures/gsd_sample.md`)
- New `Cargo.toml` aligned with `AgilePlus` workspace conventions
- New `README.md` with AI-DD badge block stripped and CLI-binary claim reworded
- 12/12 tests pass in the new location (`cargo test -p agileplus-spec-harmonizer`)

### What was NOT migrated (and why)

- **AI-DD metadata badge block** — self-described as intentional project-style
  noise; not compatible with `AgilePlus` per-crate README conventions.
- **The `agileplus-spec-harmonizer-tool` repo** — the only unique content it added
  (`docs/slsa.md` + `.github/workflows/release-attestation.yml`) is
  **byte-identical** to what `AgilePlus` already ships. Zero net content.
- **CLI binary claim in README** — the source repo's README mentions
  `cargo run -- harmonize …` but **no `src/main.rs` exists**. The crate is
  library-only; the README has been reworded accordingly.
- **`v0.1.0` git tag** — workspace re-versions under the shared workspace
  version; the GitHub tag survives archival.

### Why `agent-platform` is excluded as a target

`agent-platform` is a TypeScript ESM package implementing hexagonal ports for
**device-modality coordination** (`DeviceStage`, `AgentRuntime`, Eidolon
adapter, OTLP telemetry). Evidence for exclusion:

1. **Language mismatch.** Source is Rust 2021 with `regex` + `serde`; target
   is TypeScript with `@opentelemetry/api`. No FFI bridge exists; a full
   rewrite would be required.
2. **Scope mismatch.** Source: markdown spec-format parsers producing
   `WorkPackage[]`. Target: device-modality ports (mobile/desktop/sandbox/
   browser/vm/container) with `pointer()`, `key()`, `screenshot()`.
3. **Zero file-level matches.** `grep -r "harmoniz|spec-kat|bmad|openspec"
   ports/ package.json` in `agent-platform` returns no hits.
4. **No consumer pull.** `agent-platform` has no spec-parsing use case
   identified; the consumer for the harmonizer is `agileplus-subcmds`, which
   itself is a stub crate in the `AgilePlus` workspace.

The user's directive grouping ("both into agileplus agent-platform") is
interpreted as a category error; the only valid target for Rust spec-format
ingestion code is the `AgilePlus` Rust workspace.

## Consequences

- `agileplus/crates/agileplus-spec-harmonizer/` exists as a new workspace
  member. It is the canonical home of the 4-format spec harmonizer.
- The forward-looking "front of SDD pipeline" claim is **downgraded** in
  the new README to "designed for the `agileplus-subcmds` bridge, which
  is currently a stub crate" — this is honest about the wiring status.
- Both source repos will be archived (read-only marker) on GitHub; the
  active `gh` token lacks `delete_repo` scope, so manual UI deletion via
  Settings → Danger Zone follows after the 90-day GitHub retention window.
- `agileplus-subcmds` should evolve to consume `agileplus-spec-harmonizer`
  in a follow-up track (not in scope for this ADR).

## References

- Source repo: `<REDACTED>/agileplus-spec-harmonizer` (archived 2026-06-18)
- Source repo: `<REDACTED>/agileplus-spec-harmonizer-tool` (archived 2026-06-18)
- Target repo: `<REDACTED>/AgilePlus` (`agileplus/crates/agileplus-spec-harmonizer/`)
- Test count: 12/12 passing (`cargo test -p agileplus-spec-harmonizer`)
- Design constraint: "no async, no cgo" preserved (no `tokio` dep added)
- License: MIT OR Apache-2.0 (compatible with source MIT)
