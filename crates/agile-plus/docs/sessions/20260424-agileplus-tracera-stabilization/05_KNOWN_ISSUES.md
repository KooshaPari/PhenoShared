# Known Issues

## P0

- The current local DB still needs a live Plane push to populate mappings for
  existing features/work packages. Code paths now persist mappings when Plane
  sync runs, but no live Plane workspace was used in this session.

## P1

- FR tracker and command docs are stale against current CLI code.
- Test traceability is incomplete.
- Persisted CLI integration fixtures still need to cover validation and shipping
  governance exception rows.
- `cargo fmt --all -- --check` currently wants broad pre-existing formatting
  rewrites and reports nightly-only rustfmt options.
- Local disk is nearly full. Focused Cargo checks work after cleaning generated
  artifacts, but full workspace rebuilds can fail with `No space left on device`
  until more space is freed.

## P2

- Local runtime ports need a documented AgilePlus/Tracera coexistence contract.
- Stale status and audit docs need archive/current-state labels.
- Tracera architecture docs need alignment with its richer README/PRD surfaces.

## Resolved

- Spec truth parity for the local DB is resolved. `.agileplus/specs` now has
  canonical directories for all 19 DB feature slugs, and the two previous
  non-DB canonical directories are preserved under `kitty-specs`.
- Plane outbound decomposition is resolved. `outbound.rs` is now a facade with
  focused feature/work-package, module/cycle, and assignment modules.
- Feature and work-package Plane projection now persists `sync_mappings` with
  deterministic tests.
- SQLite adapter decomposition is resolved. `crates/agileplus-sqlite/src/lib.rs`
  is now a facade, implementations live under `src/lib/`, and
  `cargo test -p agileplus-sqlite --all-features` passes.
- `update_feature` now persists mutable fields covered by the extracted
  ContentStoragePort tests: target branch, spec hash, module id, state, slug,
  and friendly name.
- Dashboard route decomposition is resolved. `crates/agileplus-dashboard/src/routes.rs`
  is now a 91-line router facade, route handlers live under `src/routes/`, and
  `cargo test -p agileplus-dashboard --all-features` plus focused dashboard
  clippy pass.
- Frontend topology classification is resolved. `crates/agileplus-dashboard/web`
  is explicitly marked as a scaffold, and `agileplus frontend audit --strict`
  passes with unit and CLI integration coverage.
- The `plan` command no longer warns and proceeds from non-`Researched` states.
  It now fails by default and requires an explicit `--force` governance
  exception path.
- The `validate` command is no longer oversized. It now uses focused report,
  evidence/policy, and test modules.
- `validate --force`, `validate --skip-policies`, and `ship --skip-validate`
  now leave explicit governance exception evidence in reports, metadata, or
  audit transition labels.
- Custom validation policies no longer silently pass in CLI validation; they
  fail as unsupported until a real custom policy executor exists.
- Unsupported evidence threshold shapes now fail closed.
- `EvidencePresent` policies now inspect stored FR evidence instead of
  assuming success.
- Ship branch merge errors now fail the command instead of being logged and
  skipped.
- Ship worktree listing and cleanup failures are now recorded in shipped
  metadata as cleanup warnings.
- Retrospectives now detect forced, policy-skip, and skip-validate audit labels
  as governance exceptions, and suggest audited fast-track rules rather than
  silent skip rules.

## Deferred

- The dashboard web scaffold still has temporal Phase 2 docs and generated
  artifacts that should be consolidated before it is either completed as a real
  React package or archived more aggressively.
