---
repo: PhenoShared
commit: origin/main@6ec4ae563 (working tree observed at ad667428b)
date: 2026-11-10
METHOD: static inspection only — no CI run executed in this analysis, therefore NOT_RUN / UNKNOWN dominate and PASS requires observed enforcement
---

# QA Matrix - PhenoShared

Controls are read from `.github/workflows/`, repo-root tool configs. `PASS` means a workflow
that *runs* the control was observed in this inspection. `WEAK` means the tool exists but its
wiring is partial or scoped. `UNKNOWN` means the config exists but no enforcement path was
observed. No live CI run, branch-protection query, or check-run lookup was performed.

## Verdict summary

| Verdict | Count | Meaning |
|---|---|---|
| PASS | 12 | Control observed wired into at least one workflow on push/PR |
| WEAK | 2 | Tool config exists; enforcement partial, scoped, or unproven |
| UNKNOWN | 2 | Config exists; no enforcing path observed; UNKNOWN, not FAIL |
| GAP | 0 | No separate GAP verdict; unproven controls are recorded in the gaps register |
| NOT_RUN | 0 | No executed run in this analysis |
| **Total** | **16** | |

## Control matrix: build, test, and integration gates

| # | Dimension | Control | Exists | Location | Enforced in CI | Failure mode | Evidence | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | Testing | Unit tests (Rust) | Yes | `ci.yml` (cargo nextest), `quality-gate.yml` (`make check`), `reusable-test.yml` | Yes — push/PR/merge_group | Silent test regression; no nextest run blocks | nextest invocation present in `ci.yml` | PASS |
| 2 | Testing | Integration tests | Yes | `reusable-test.yml`, `iac-rust.yml`, `ffi-ci.yml`, `libs-activation-ci.yml` | Yes | Cross-crate breakage lands unchecked | reusable test workflow invoked from multiple callers | PASS |
| 3 | Testing | E2E smoke | Yes | `e2e.yml` — `--test e2e_smoke --no-fail-fast --locked` + daemon health job | Yes — dedicated workflow | Daemon start/health regressions undetected | explicit smoke bin + `nc` health probe | PASS |
| 4 | Testing | Python tests | Yes | `reusable-test.yml`, `ai-testing-orchestration.yml` (pytest) | Yes | Python surface untested | pytest step present | PASS |
| 5 | Testing | Browser E2E (Playwright) | Yes | `reusable-a11y.yml`, `ai-testing-orchestration.yml` | Yes | UI regressions undetected | Playwright step present | PASS |
| 6 | Coverage | Coverage floor (aggregate 36.00) | Yes | `.coverage-baselines/root-workspace.toml`, `coverage.yml`, `.github/scripts/coverage_report.py` | Yes — push(main) + PR(main) | Floor is low: 36% against ~19.2k test attributes in `crates/` (measured 2026-11-10T10:53Z: `#[test]` 16,266 + `#[tokio::test]` 2,955 = 19,221; the bare-`#[test]` half drifted 16,216 → 16,266 → 16,712 across three reads because another process is re-checking-out this tree during the analysis, so treat the total as ~19.2k, not an exact constant) | measured floor `aggregate_floor = 36.00` (verified) | PASS |
| 7 | Coverage | Codecov status gate | Config only | `.github/codecov.yml` — project 71%, patch 80%, threshold 1% | No upload step observed | Gate may never receive a report; targets aspirational | no workflow step uploading to Codecov located | UNKNOWN |
| 8 | Coverage | Ratchet (js-coverage job) | Yes | `ratchet.yml` | Unproven | Job's own comment records bun/`npm ci` failure on `workspace:*` | in-file comment only; effectiveness UNKNOWN without a run | UNKNOWN |
| 9 | Static analysis | clippy `-D warnings` | Yes | `reusable-lint.yml`, `quality-gate.yml`, `iac-rust.yml`, `tf-ci.yml` | Yes | Lint drift on new code | `--workspace --all-targets -- -D warnings` present | PASS |
| 10 | Static analysis | cargo-deny (advisories + licenses) | Yes | `deny.toml`, `cargo-deny.yml`, `deny.yml`, `ci.yml`, `license-compliance.yml` | Yes | Supply-chain / license drift | `deny.toml` with 12 RUSTSEC ids, 18 SPDX allow-ids | PASS |
| 11 | Static analysis | CodeQL | Yes | `codeql.yml`, `.github/codeql/`, `security.yml` rust job | Yes | Vuln classes go unscanned | CodeQL job present in two workflows | PASS |
| 12 | Formatting/lint | rustfmt `--check` | Yes | `Makefile: fmt` → `cargo fmt --all --check`; `reusable-lint.yml` | Yes | Format drift blocks nothing | `make check` = fmt + clippy + test-unit | PASS |
| 13 | Formatting/lint | trunk (multi-linter) | Yes | `trunk.yaml`, `.trunk/`, `trunk-check.yml` (PR + push + weekly cron) | Yes — no `continue-on-error` in trigger/step region | Mixed-linter drift | workflow read for trigger/steps; exit-code semantics unconfirmed | PASS |
| 14 | Formatting/lint | typos | Partial | `.typos.toml`, `_typos.toml`; `crate-ci/typos` in `compute-infra-auditors.yml` only | Weak — absent from `ci.yml`, `quality-gate.yml`, `trunk-check.yml` | Misspellings outside one workflow pass unblocked | not a trunk plugin; single-workflow scope | WEAK |
| 15 | Formatting/lint | commitlint (conventional commits) | Partial | `.commitlintrc.json`, `.commitlintrc.yml`; `pr-lint.yml` = "Lint PR title" | PR-title scope only; no commit-msg hook proven | Non-conventional commit messages unblocked | only wiring is PR-title lint | WEAK |
| 16 | Formatting/lint | markdownlint | Yes | `.markdownlint.json`, `.markdownlint.yaml`; `docs-check.yml` | Yes (docs scope) | Doc lint drift within docs scope | markdownlint invoked from docs-check | PASS |

Notes: "Enforced in CI" records that a workflow *runs* the control, not that the check is a
required status on `main` — required-check status was not queried (`gh api` out of scope).

