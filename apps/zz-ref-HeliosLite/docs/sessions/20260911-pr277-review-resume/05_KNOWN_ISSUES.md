# Remaining integration blockers

## Hosted failures observed on 2026-09-11
The handoff's all-green hosted status is stale. Current PR head is `a6568db88d8785fe95939b0863d299ba185d7d9d`.

- cargo-deny run `34594430856`: `forge_lsp v0.1.0 is unlicensed`. Advisories and sources passed.
- Lint Fix run `34594430992`: `clippy::string_slice` errors at `crates/forge_lsp/src/tsc.rs:116,120,121`.
- `forge_lsp` is absent from this integration checkout and its workspace member list. It exists on the PR's base `main`. Do not fabricate a replacement crate in this branch. These failures require validation/fixes against the actual merge result or a separate base-branch change.
- Kilo Code Review fails. An earlier CodeRabbit summary attributes a Kilo failure to the model output limit. Do not claim current Kilo failure is cleared.
- CodeRabbit still has a `CHANGES_REQUESTED` review. Passing local checks does not clear that review.

## forge_lsp failures (pre-existing on main)

`forge_lsp` is absent from the integration branch. It exists on `main` (`04f5dcaba`) with two defects:
- Missing `license` field in Cargo.toml (cargo-deny rejects as unlicensed)
- `clippy::string_slice` violations in `src/tsc.rs:116,120,121`

These are NOT caused by PR #277. They fail in the merge-to-main CI checks (`Lint Fix`, `cargo-deny`) because the merge result includes `main`'s code. Fixing them requires either:
1. A separate PR to `main` that adds the license and fixes the clippy issues
2. Including the fix on the integration branch before merge

This is out of scope for the current review-fix work. Per CI billing policy, merge/billing-error CI failures on these checks do not block merge if core checks (clippy, tests, fmt on the PR branch) pass.

## CodeRabbit review

Thread resolution summary posted to PR. Re-review requested via `@coderabbitai` mention. The `CHANGES_REQUESTED` review state blocks merge until cleared.
Bounded returned results and streaming candidates do not imply bounded worst-case CPU or total I/O. A compressed history with no matches may require scanning all eligible candidates. An arbitrary candidate SQL limit would silently omit older matches and is not an acceptable workaround.

## Release boundary
No merge, signed release, installation smoke run, or Vite dependency remediation is claimed complete. Review-fix publication must preserve the fork's latest head and never force-push.
