<!-- Base: platforms/thegent/governance/AGENTS.base.md (external repo; not vendored here) -->
<!-- Last synced: 2026-08-02 -->

# AGENTS.md — helios-cli

Working tree of `KooshaPari/helios-cli`, a hard fork of `openai/codex`.
Read `CLAUDE.md` (in-repo) for governance and branch discipline, and
`ARCHITECTURE.md` for the hard-fork/dual-workspace model.

## Project Identity & Work Management

### Project Overview

- **Name**: helios-cli
- **Description**: Phenotype harness + Codex-derived CLI. Dual workspace:
  a root Rust workspace of ~21 harness crates (`crates/`), plus vendored
  upstream trees `codex-rs/` (120+ crates, separate workspace root, excluded
  from the root `Cargo.toml`) and `helios-rs/`, an npm package `codex-cli/`,
  a Python harness (`harness/`), and a Python router UI (`src/helios_router_ui/`).
- **Location**: repo-relative — this checkout. No machine-specific absolute
  paths (do not introduce any; use `./` or `$HOME/...`).
- **Language Stack**: Rust (root edition 2021; codex-rs edition 2024),
  Python (harness, router UI), TypeScript (codex-cli).
- **Published**: internal hard fork.

### AgilePlus Integration

All work MUST be tracked in the external AgilePlus service. The tracker is
not a source repository for HeliosCLI work and is not mirrored into this
repository.

- Cite `AP-ITEM:<id>` for a queued external work item.
- Cite `AP-FEATURE:<slug>/WP<n>` when the external service has created a
  feature and work package.
- Put the identifier in the branch, commits, and pull-request body.
- Do not create, copy, or commit AgilePlus tracker artifacts (`kitty-specs/`,
  worklogs, or tracker database state) in either the AgilePlus source repo or
  this repository. Product requirements in `docs/functional-requirements/`
  remain HeliosCLI documentation; they are not tracker mirrors.

**Requirements**:

1. Create or reference an external AgilePlus work-item identifier before implementation.
2. Record the item's scope and acceptance criteria in the external tracker.
3. Update the external item as work progresses when its service interface is available.
4. No untracked code: every implementation change must cite its external AgilePlus item.

---

## Repository Mental Model

### Project Structure

```
Cargo.toml            # root harness workspace (members under crates/; excludes codex-rs/, helios-rs/, crates/harness_pyo3)
justfile              # task runner: check / build / test / lint / fmt-check / audit
crates/               # harness crates: harness_queue, harness_runner, harness_scaling,
                      #   harness_schema, harness_spec, harness_checkpoint, harness_verify,
                      #   harness_utils, harness_cache, harness_discoverer, harness_elicitation,
                      #   harness_interfaces, harness_normalizer, harness_orchestrator,
                      #   harness_rollback, harness_teammates, harness_recorder, arch_test,
                      #   helios_config, pheno-plugin, plugin-arch
codex-rs/             # VENDORED openai/codex Rust workspace (120+ crates) — separate root, EXCLUDED from root workspace
codex-cli/            # VENDORED npm package tree (TypeScript)
helios-rs/            # VENDORED helios-rs workspace — EXCLUDED from root workspace
harness/              # Python harness (src/harness/, tests/, benchmarks/)
src/helios_router_ui/ # Python router UI (Streamlit)
docs/                 # functional-requirements/ (FR-*), adrs/, security/threat-model.md, slsa.md, index.md
.github/              # workflows/ (rust-ci.yml, ci.yml, rust-release.yml, cargo-deny.yml, ...),
                      #   ISSUE_TEMPLATE/, pull_request_template.md, CODEOWNERS
tests/                # root integration tests (e2e_smoke.rs)
```

### Build Model (IMPORTANT)

- The root workspace is small and fast: `cargo check --workspace` /
  `cargo test --workspace` are the primary loops. The required CI gate is the
  `workspace` job in `.github/workflows/rust-ci.yml`.
- `codex-rs/` is a separate 120+ crate workspace: **never** run full
  `cargo build`/`cargo test`/`cargo clippy` there locally — it takes hours.
  Work on it only via `cargo check -p <specific-crate>` when strictly needed.
- `crates/harness_pyo3` is excluded from the root workspace (broken path dep
  `phenotype-shared`); leave it excluded.

### Style Constraints

- **Line length**: 100 characters (Rust convention)
- **Formatter**: `cargo fmt` (mandatory)
- **Type checker**: Rust compiler (strict)
- **Linter**: `cargo clippy --workspace --all-targets -- -D warnings` (zero warnings)
- **File size target**: ≤350 lines per source file, hard limit ≤500 lines
- **Typing**: Full type annotations required; no `impl Trait` in public APIs

### Key Constraints

- All CLI commands use `clap` for argument parsing
- Error handling via `thiserror` with clear error types
- Async code uses `tokio` runtime
- No global state; dependency injection for configuration
- Tests verify both happy path and error conditions
- Do NOT add `continue-on-error: true` or `|| echo "::warning::"` swallows to
  CI gates — failing checks must fail the workflow

---

## Build / Test / Lint

Prefer the justfile recipes (they wrap the root workspace):

```bash
just check       # cargo check --workspace --all-targets
just build       # cargo build --workspace
just test        # cargo test --workspace
just lint        # cargo clippy --workspace --all-targets -- -D warnings
just fmt-check   # cargo fmt --all -- --check
just audit       # verify-governance + verify-codeowners
```

Plain cargo equivalents work from the repo root:

```bash
cargo check --workspace --all-targets
cargo test --workspace
cargo fmt --all -- --check
```

## Key Files

- `Cargo.toml` — root workspace manifest (members + excludes)
- `justfile` — canonical task commands
- `ARCHITECTURE.md`, `ADR.md` — architecture and decisions
- `docs/functional-requirements/` — FR-\* specs (SHALL statements); tests must
  trace to them
- `docs/security/threat-model.md`, `docs/slsa.md` — security posture and
  supply-chain claims (keep truthful: `docs/slsa.md` must match what
  `.github/workflows/rust-release.yml` actually wires)
- `.github/workflows/rust-ci.yml` — required CI gate (workspace/deny/aggregator)
- `.github/workflows/ci.yml` — generic lint/test gates (fail-hard by design)
- `.github/workflows/rust-release.yml` — release pipeline incl. `attest`
  (SLSA build provenance) job
- `deny.toml`, `renovate.json` — dependency/license policy

## Forbidden Ops

1. **Never** run a full build/test/clippy of the vendored `codex-rs/` workspace locally.
2. **Never** commit scratch files: `build-*.txt`, `codex-build-*.txt`, `*.bat`/
   `*.vbs`/`*.cmd` scratch scripts at root, `__pycache__/`, `*.exe` at root,
   `NONE`, `_c.txt`, `*.log` leftovers.
3. **Never** weaken CI: no `continue-on-error`, no `|| echo ::warning::`
   swallows, no tag-pin→`@main` downgrades on security actions.
4. **Never** force-push to `main` or shared branches; no direct pushes to
   `main` — work in a branch/worktree and open a PR. Mergify requires the
   configured green checks, conflict-free state, and resolved conversations;
   it does not require a human approval.
5. **Never** commit secrets — `auth.json`, tokens, AKV credentials, `.env`
   files. CI runs trufflehog + gitleaks and will fail.
6. Do not edit vendored code in `codex-rs/` without an upstream-tracked
   rationale (see `docs/upstream-research/`).

---

## Worktree & Parallel-Agent Discipline

- Do work in a dedicated branch or worktree (`git worktree add`), one topic
  per branch; never run two agents mutating the same worktree.
- Before starting, check `git status -sb` is clean of scratch files; run
  `git pull --ff-only` / rebase on `main` before pushing.
- Tests are hermetic (temp paths; smoke tests spawn their own manifest) — run
  them in parallel freely, but do not share `target/` between concurrent
  `cargo` processes of different toolchains.

---

## Session Documentation

All agents MUST maintain session documentation for research, decisions, and findings:

### Location

- Default: `docs/sessions/<session-id>/`

### Standard Session Structure

```
docs/sessions/<session-id>/
├── README.md           # Overview and context
├── 01_RESEARCH.md      # Findings and analysis
├── 02_PLAN.md          # Design and approach
├── 03_IMPLEMENTATION.md # Code changes and rationale
├── 04_VALIDATION.md    # Tests and verification
└── 05_KNOWN_ISSUES.md  # Blockers and follow-ups
```

---

## Quality Standards

### Code Quality Mandate

- **All linters must pass**: `cargo clippy --workspace --all-targets -- -D warnings`
- **All tests must pass**: `cargo test --workspace`
- **No AI slop**: Avoid placeholder TODOs, lorem ipsum, generic comments
- **Backwards incompatibility**: No shims, full migrations, clean breaks

### Test-First Mandate

- **For NEW modules**: test file MUST exist before implementation file
- **For BUG FIXES**: failing test MUST be written before the fix
- **For REFACTORS**: existing tests must pass before AND after

### FR Traceability

All tests MUST reference a Functional Requirement (FR) from
`docs/functional-requirements/`:

```rust
// Traces to: FR-HELIOS-NNN
#[test]
fn test_feature_name() {
    // Test body
}
```

---

## Quick Reference Commands

```bash
# Run all quality checks (root workspace only)
just check
just lint
just fmt-check
just test

# Run specific test
cargo test -p <crate> <test_name>

# Check a single crate (fast)
cargo check -p <crate>

# List tasks / repo meta
just
just meta

# Governance audit (requires .github/pull_request_template.md etc.)
just audit
```
