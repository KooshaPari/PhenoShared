# BLOCK A app trio — absorb intent (proposed)

## Status: **proposed cross-reference; no destructive history rewriting performed**

Three repos on the KooshaPari account share the same Anthropic
"Block A" starter-template description and exist as parallel
implementations of the same scaffolding intent:

| Repo | Language | Files | Default branch | Description (truncated) | Last push |
|---|---|---|---|---|---|
| `KooshaPari/Apisync` | Rust | 128 | `main` | Anthropic Block A app for Claude-Computer-Use | 2026-09-09 |
| `KooshaPari/DataKit` | Python | 47 | `main` | Anthropic Block A app for Claude-Computer-Use | 2026-09-09 |
| `KooshaPari/Stashly` | Rust | ~50 | `main` | Anthropic Block A app for Claude-Computer-Use | 2026-09-09 |

## Why absorb (the why, recorded)

The three repos are parallel implementations of the same starter
template. Each carries its own `AGENTS.md`, `CLAUDE.md`, `.github/`,
`Cargo.toml` / `pyproject.toml`, and pre-commit hooks — a literal
`git subtree merge` would produce hundreds of trivial file collisions
on metadata files whose only difference is the repo name. The
intent to consolidate is real, but the historical register cannot be
silently adopted (per EXECUTION-CORRECTION rule: "Do not silently
adopt a historical register recommendation").

## Recommended path (operator call)

1. **Spawn a new canonical starter:** `KooshaPari/ComputerUse-Starter`
   (Rust + Python subdirs). Empty; designed to receive `git subtree
   add` from the three sources in a single PR.
2. **`git subtree add --prefix=rust-apisync Apisync main`** on the
   new canonical repo.
3. **`git subtree add --prefix=python-datakit DataKit main`**.
4. **`git subtree add --prefix=rust-stashly Stashly main`**.
5. **Resolve trivial collisions** (`AGENTS.md`, `CLAUDE.md`,
   `.github/workflows/`, `.gitignore`) by accepting the canonical's
   variants per-language and adding a top-level
   `CROSS-REFERENCES.md` documenting the move.
6. **Operator-driven archive** of `Apisync`, `DataKit`, `Stashly`
   via `gh repo archive KooshaPari/Apisync` etc. (this is
   **public + irreversible in social terms**; only the operator
   should trigger).

## What this PR does NOT do

- No `git subtree` invocation against the historical repos
- No archive flag toggled on any source repo
- No file move or rename within the historical repos
- No CI workflow modifications

## What this PR does

- Adds this `BLOCK-A-TRIO.md` to `Apisync` documenting the absorb
  intent and the recommended operator-driven path
- Records the same intent in the corresponding
  `.handoff-evidence/2026-09-08T2151Z/Apisync-BLOCK-A-TRIO.md`
  for the central audit ledger

## Cross-reference

- `phenotype-registry/audits/absorption-justifications/` may want a
  new `Apisync-2026-09-09.md` entry recording this absorb intent
  (registry-owned; out-of-scope here).
