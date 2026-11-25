# Plan — Action Hygiene (eco-011)

## Objective

Eliminate unpinned and malformed third-party `uses:` references across the
Phenotype org workflow files. Drive unpinned < 5 and malformed = 0, with CI
green on the touched repos.

## Scope

This pass covers the five most-used actions only (the bulk of the 1071
unpinned refs):

1. `actions/checkout`
2. `dtolnay/rust-toolchain`
3. `github/codeql-action/upload-sarif`
4. `Swatinem/rust-cache`

Tag-style refs `@v4`, `@v6`, `@stable`, `@v2` are the targets. Malformed refs
are folded into the same sweep — they are recovered from the audit JSON by
matching ref-shape to the canonical action set.

Out of scope: less-used actions with single-digit counts (handled in a
follow-up sweep to keep this pass auditable).

## Implementation Steps

1. **Resolve SHAs.** For each of the five actions, query the upstream
   default branch (`HEAD` via `git ls-remote` against the public repo) and
   record the 40-char commit SHA. Cache the SHAs in a sibling JSON so step 2
   can run without network.
2. **Fan out per-repo worktrees.** Spawn one worker per repo carrying the
   affected workflows. Each worker rewrites every `uses:` line for the five
   scoped actions to `uses: <action>@<40-char-sha>`, regenerates the audit,
   and emits a per-repo dirty commit on the existing branch. Malformed refs
   are rewritten to the same SHA once their intended action is identified;
   the remaining 384 are quarantined into `audit/quarantine-20260605.json`
   for manual triage.
3. **Verify CI.** Each worker runs `task quality` (or the repo's local
   equivalent: `cargo test --workspace && cargo clippy --all -D warnings`
   for Rust, `pnpm test` for TS, `pytest` for Python). Workers report green
   or fail the WP.
4. **Aggregate.** Merge per-repo branches into a roll-up branch; re-run the
   audit script; confirm AC-1..AC-3.
5. **Follow-up sweep.** Schedule eco-012 to clear the residual unpinned and
   quarantined malformed refs.

## Phased WBS

| Phase | WP | Description | Depends On |
|---|---|---|---|
| Discovery | WP-01 | Resolve 5 SHAs, freeze audit input | — |
| Discovery | WP-02 | Triage 384 malformed refs into action bins | WP-01 |
| Build | WP-03 | Fan-out rewrites per repo, per-provenance commits | WP-01, WP-02 |
| Validate | WP-04 | Per-repo local CI + org audit rerun | WP-03 |
| Handoff | WP-05 | Roll-up branch, follow-up eco-012 spec drafted | WP-04 |
