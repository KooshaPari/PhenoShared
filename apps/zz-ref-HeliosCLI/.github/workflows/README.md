# Workflow Strategy

AgilePlus traceability is external. Cite `AP-ITEM:<id>` or
`AP-FEATURE:<slug>/WP<n>` in the associated pull request; do not link a local
tracker artifact.

The workflows in this directory are split so that pull requests get fast, review-friendly signal while optional vendored/upstream trees stay off the critical path.

## Active harness gate (required for green main)

- `rust-ci.yml` — primary Cargo workspace check for root harness crates (`cargo build/test/clippy/fmt` + `cargo-deny`).
- `ci.yml` — README ASCII/ToC + Node staging checks.
- `cargo-deny.yml` — license/advisory policy via EmbarkStudios/cargo-deny-action (root `deny.toml`).

Mark **`CI results (required)`** (from `rust-ci.yml`) and/or the `workspace`/`deny` jobs as branch-protection required checks. Prefer those over Bazel/SDK/Format/shear/ACL.

## Vendored / upstream paths (disabled for hard-fork green)

`codex-rs/` and `codex-cli/` are **excluded** from the root Cargo workspace (see `ARCHITECTURE.md`). These workflows/jobs are kept in-tree but gated with `if: false` (or path filters) and should **not** be required status checks:

- `bazel.yml` — all jobs `if: false` (BuildBuddy / self-hosted runners).
- `sdk.yml` — all jobs `if: false` (self-hosted `*-runners`).
- `rust-ci.yml` Format / cargo shear / argument-comment-lint (ACL) — `if: false`.

Re-enable by flipping the job `if:` conditions when runners and Bazel credentials are available.

## Rule Of Thumb

- Harness-only / hard-fork green: expect `rust-ci` (`workspace` + `deny` + aggregator) + `ci` (+ `cargo-deny`) green; Bazel/SDK/Format/shear/ACL stay skipped.
- Keep harness `rust-ci.yml` `workspace`/`deny` jobs as the default required gate.
