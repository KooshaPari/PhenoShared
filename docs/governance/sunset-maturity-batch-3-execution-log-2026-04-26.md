# Sunset Maturity Batch 3 Execution Log - 2026-04-26

## Purpose

Record live execution after batch 2: safe ruleset tightening, fresh clone repair path,
and the blocked `phenotype-errors` release-prep lane.

## Executed Changes

### `phenoShared` Ruleset Tightening

Updated live GitHub ruleset `Main Governance Baseline` (`14279307`) for
`<REDACTED>/phenoShared`.

Before:

- `required_approving_review_count = 0`
- `required_review_thread_resolution = false`
- `require_code_owner_review = false`

After:

- `required_approving_review_count = 1`
- `required_review_thread_resolution = true`
- `require_code_owner_review = false`

`require_code_owner_review` intentionally remains disabled. The active
`.github/CODEOWNERS` currently assigns all files to `@<REDACTED>`, and GitHub does
not allow PR authors to approve their own required review. Enabling code-owner review
without adding another write-capable owner would self-block maintenance.

### PhenoKits Fresh Clone Verification

The shelf-level checkout at `/Users/<REDACTED>/CodeProjects/Phenotype/repos` still has
missing tree objects and should remain quarantined for root branch switching.

A fresh clone was verified at:

```text
/tmp/phenokits-fresh.TDBzua/PhenoKits
```

Validation:

- `git fsck --full --no-reflogs --strict` passed.
- `git status --short --branch` showed clean `main...origin/main`.
- `git count-objects -vH` showed `garbage: 0`.

Use the fresh clone for future PhenoKits governance PRs until the shelf checkout is
repaired or replaced.

### `phenotype-errors` Release Prep Blocked

The intended Rust-crate release-prep lane is blocked because the current `phenoShared`
checkout does not contain `crates/phenotype-errors`.

Current reality:

- `phenoShared/Cargo.toml` does not list `phenotype-errors`.
- `phenoShared/crates/phenotype-errors` is absent.
- A JS package exists at `phenoShared/packages/errors` as `@phenotype/errors`.
- That JS package is not fully release-ready: missing package README, package
  CHANGELOG, and richer publish metadata.

Decision required before implementation:

- If the target is Rust, create `crates/phenotype-errors` and add workspace metadata.
- If the target is JS, prepare `packages/errors` for package release instead.

Do not create a Rust crate just to satisfy an old audit assumption.

## PR Queue Maintenance

The following simple single-file README PRs appeared during this batch and were
admin-merged:

- `<REDACTED>/eyetracker#2`
- `<REDACTED>/TestingKit#7`
- `<REDACTED>/heliosBench#123`
- `<REDACTED>/HeliosLab#56`
- `<REDACTED>/helios-router#184`

## Next Actions

1. Add a second write-capable code owner or team to `phenoShared` before enabling
   code-owner review.
2. Decide Rust vs JS target for the `phenotype-errors` release-prep lane.
3. Continue PhenoKits governance docs from the fresh clone, not the corrupted shelf
   checkout.
4. Generate per-repo P0 branch-tip manifests under `worklogs/p0-drift/`.
