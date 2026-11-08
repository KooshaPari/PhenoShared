# Tasks: Org Sunset Maturity Program

## P0

- [x] SUNSET-001: Create current repo-state ledger with all active/archived repos and maturity state.
  - Evidence: `docs/governance/current-repo-state-ledger-2026-04-26.md`
- [x] SUNSET-002: Produce updated initial dispositions for `agentapi-plusplus`, `phenoSDK`, `PhenoProc`, `Dino`, `PhenoSpecs`, shelf root, and `AuthKit/go`.
  - Evidence: `worklogs/P0_DRIFT_DISPOSITION_2026_04_26.md`
- [x] SUNSET-003: Decide `AuthKit/go` policy: submodule, vendored nested repo, or flattened directory.
  - Evidence: `docs/governance/authkit-go-ownership-policy-2026-04-26.md`
- [ ] SUNSET-003A: Create/identify `AuthKit/go` remote and register it as a real submodule.
- [ ] SUNSET-003B: If no remote is created, flatten `AuthKit/go` only after preserving nested history.
- [ ] SUNSET-004: Create shared-crate canonical-home implementation PR for Phase 1 crates into `phenoShared`.
- [x] SUNSET-004A: Decide errors dual-interface strategy before implementing release prep.
  - Evidence: `docs/governance/adr-2026-04-26-errors-dual-interface-strategy.md`
- [x] SUNSET-004B: Define target file map and API surface for errors dual-interface implementation.
  - Evidence: `docs/governance/errors-dual-interface-target-state-2026-04-26.md`
- [x] SUNSET-004C: Open dual-interface errors implementation PR in `phenoShared`.
  - Evidence: `phenoShared#109`, `docs/governance/sunset-maturity-batch-5-review-gate-plan-2026-04-26.md`
- [x] SUNSET-004D: Open config-core validation unblocker PR in `phenoShared`.
  - Evidence: `phenoShared#110`, `docs/governance/sunset-maturity-batch-5-review-gate-plan-2026-04-26.md`
- [ ] SUNSET-004E: Review-gated merge of `phenoShared#110` before workspace-wide validation claims.
- [ ] SUNSET-004F: Review-gated merge of `phenoShared#109` before release-prep or consumer migrations.

## P1

- [ ] SUNSET-005: Inventory rulesets for all active repos and classify missing/weak/strong.
- [x] SUNSET-005A: Sample priority rulesets and record blocked vs actionable gaps.
  - Evidence: `docs/governance/ruleset-gap-ledger-2026-04-26.md`
- [ ] SUNSET-006: Apply governance baseline to priority rule-less repos after CI truth is known.
- [x] SUNSET-006A: Tighten `phenoShared` live ruleset without enabling self-blocking CODEOWNER review.
  - Evidence: `docs/governance/sunset-maturity-batch-3-execution-log-2026-04-26.md`
- [x] SUNSET-006B: Record review-gated queue and merge order after ruleset tightening.
  - Evidence: `docs/governance/sunset-maturity-batch-5-review-gate-plan-2026-04-26.md`
- [ ] SUNSET-007: Inventory stale no-PR branches and capture tip SHAs.
- [ ] SUNSET-008: Prune only merged or superseded stale branches.
- [x] SUNSET-008A: Inventory worktree/recovery containers before pruning.
  - Evidence: `worklogs/WORKTREE_QUARANTINE_LEDGER_2026_04_26.md`

## P2

- [ ] SUNSET-009: Consolidate dated worklogs into category worklogs.
- [ ] SUNSET-010: Review temporary/deleted governance docs for unique content before deletion.
- [x] SUNSET-011: Resolve `Tracera` vs `Tracera-recovered` canonical checkout and document final routing.
  - Evidence: `docs/governance/tracera-canonical-routing-2026-04-26.md`
- [x] SUNSET-011A: Fresh-clone compare `<REDACTED>/Tracera.git` against `Tracera-recovered`.
  - Evidence: `docs/governance/tracera-fresh-clone-compare-2026-04-26.md`
- [ ] SUNSET-011B: Promote recovered checkout or push missing recovery branch.
- [ ] SUNSET-011C: Route `phench/` to its own repository/product home.

## P3

- [ ] SUNSET-012: For each `SUNSET_READY` repo, add successor/canonical-home README note.
- [ ] SUNSET-013: Remove Dependabot configs before archive.
- [ ] SUNSET-014: Publish final org maturity ledger and acceptance evidence.
- [x] SUNSET-014A: Verify fresh PhenoKits clone for future governance work while shelf checkout remains quarantined.
  - Evidence: `docs/governance/sunset-maturity-batch-3-execution-log-2026-04-26.md`
