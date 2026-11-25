# DAG WBS

## Completed In This Session

1. Workspace manifest repair
   - Add missing fixture crate manifest.
   - Register local workspace crates.
   - Replace stale plugin Git dependency with local crate.

2. Compile and lint repair
   - Update stale test builders and imports.
   - Add missing shared API/error/macro crates.
   - Clear strict clippy warnings across touched packages.

3. Runtime path repair
   - Point `scripts/dev-up.sh` at `process-compose.yml`.
   - Move Plane API/worker/beat paths from removed `apiserver` to
     `.agileplus/plane/apps/api`.
   - Move Plane web path from removed `.agileplus/plane-web` to
     `.agileplus/plane/apps/web`.
   - Use local runtime port variables in Plane and AgilePlus compose entries.

4. Spec audit command
   - Add `agileplus specs audit`.
   - Add JSON and strict modes.
   - Read feature slugs through a slug-only SQLite query so legacy timestamp
     rows do not block governance reconciliation.
   - Add CLI integration tests for legacy-only, strict-failing, and clean
     canonical spec states.

5. Plane sync mapping storage baseline
   - Add SQLite repository tests for sync mapping upsert, update, Plane-ID
     lookup, and delete.

6. Plane outbound projection
   - Decompose the 498-line `crates/agileplus-plane/src/outbound.rs` facade into
     feature/work-package, module/cycle, and assignment modules.
   - Add storage-aware feature and work-package push functions.
   - Persist `sync_mappings` rows with entity types `feature` and
     `work_package`.
   - Wire CLI planning and assignment paths through environment-gated Plane sync
     helpers.

7. Decomposition and frontend topology gates
   - Split `crates/agileplus-sqlite/src/lib.rs` into a facade and focused
     adapter/trait/test modules.
   - Split `crates/agileplus-dashboard/src/routes.rs` into focused route
     modules under `src/routes/`.
   - Add `agileplus frontend audit`.
   - Mark `crates/agileplus-dashboard/web` as an explicit scaffold with
     `FRONTEND_STATUS.md`.

8. First governance enforcement slice
   - Change `agileplus plan` from warn-and-proceed to fail-by-default when the
     feature has not reached `Researched`.
   - Add explicit `--force` override and record forced audit transition text.
   - Add CLI integration coverage for strict failure and forced planning.
   - Split `crates/agileplus-cli/src/commands/plan.rs` below the target line
     count by activating `plan/artifacts.rs`, `plan/parsing.rs`, and
     `plan/tests.rs`.

9. Validation and shipping governance hardening
   - Split `crates/agileplus-cli/src/commands/validate.rs` below the target
     line count by activating `validate/report.rs`, `validate/evidence.rs`,
     and `validate/tests.rs`.
   - Keep `validate --force` and `validate --skip-policies` as explicit
     governance exceptions in reports and audit transition labels.
   - Change custom policy checks from silent pass/skip to validation failure
     with an unsupported-policy message.
   - Change unsupported evidence threshold shapes to fail closed.
   - Evaluate `EvidencePresent` policies against stored FR evidence instead of
     assuming success.
   - Keep `ship --skip-validate` as an explicit governance exception in
     shipped metadata and audit transition labels.
   - Change ship branch merge errors from warning-and-skip to hard failures.
   - Record ship cleanup warnings in shipped metadata rather than swallowing
     worktree listing/cleanup failures.
   - Update retrospectives to detect forced, policy-skip, and skip-validate
     audit labels and suggest audited fast-track policy instead of silent skip
     policy.

## Remaining Critical Path

1. Governance enforcement
   - Add persisted CLI integration fixtures for validation and shipping
     governance exception rows.
   - Add end-to-end CLI fixtures for validation and shipping exception paths
     after the command-level unit coverage is stable.
   - Regenerate or replace stale FR tracker docs.

2. Projection contracts
   - Run a live Plane push against a configured Plane workspace to populate
     local DB mappings for existing features/work packages.
   - Add API-level or CLI-level smoke coverage for environment-gated sync.
   - Define AgilePlus-to-Tracera import contract.
   - Add receiver-side Tracera tests before cloud integration work.

3. Frontend stabilization
   - Keep Rust dashboard as production local UI until a complete MFE exists.
   - Consolidate `crates/agileplus-dashboard/web` Phase 2 temporal docs and
     generated artifacts.
   - If revived later, complete the React package manifest, app entrypoints,
     lockfile, and build/test/storybook gates before changing its status.

4. Decomposition
   - Keep `crates/agileplus-sqlite/src/lib/storage_port.rs` under watch; it is
     at the 350-line target and should split if new storage methods are added.
   - Keep `crates/agileplus-cli/tests/cli_integration.rs` under watch; it is
     below the hard limit but should split by command concern if more CLI
     scenarios are added.
   - Later split Tracera oversized recovered routers after AgilePlus gates stay
     clean.

5. WBS and release readiness
   - Produce an AgilePlus-to-Tracera contract spec and tests.
   - Re-run full workspace clippy/test once local disk has enough free space for
     a full rebuild.
   - Prepare a landing branch/PR split that keeps unrelated dirty work isolated.
