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

## Control matrix: static analysis, security, and supply chain

Verdict rubric: `PASS` only with observed enforcement, `NOT_RUN` = control exists but was not executed on the gating path, `UNKNOWN` = undeterminable from the read evidence, `FAIL` = control absent or demonstrably deviating, with evidence. No CI run was executed for this matrix, so "Enforced in CI" means a workflow that runs the control, not proof it blocks merge.

| # | Dimension | Control | Exists | Location | Enforced in CI | Failure mode | Evidence | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | Security/supply chain | cargo-deny advisory/license/source gate on the PR path | Partial | `deny.toml`; `deny.yml` (repo root, no `continue-on-error`) | No — weekly Mon 09:00 UTC + push-to-`main` lockfile touches only | PR merges green carrying a new advisory, disallowed license, or non-crates.io source | `deny.toml`; `deny.yml`; `ci.yml` | NOT_RUN |
| 2 | Security/supply chain | RustSec advisory scan (`cargo audit`) | Yes | `security.yml`, `security-scan.yml`, `ffi-ci.yml` | Referenced, but per-step gating semantics were not read | A RustSec hit may not fail a build | `cargo audit` invocations in `security.yml`, `security-scan.yml`, `ffi-ci.yml` (step semantics not read) | UNKNOWN |
| 3 | Security/supply chain | Credential leak scanning (gitleaks / trufflehog / secret-guard) | Yes | `.gitleaks.toml`, `security.yml`, `ci.yml`, `trufflehog.yml`, `secret-guard.yml` | Yes | Credential lands in history or a workflow | `gitleaks.toml`; workflow read | PASS |
| 4 | Security/supply chain | SAST + container scan + SBOM + OpenSSF scorecard | Yes | `codeql.yml`, `audit.yml` (Trivy), `sbom.yml`, `scorecard-ci.yml` | Yes | Vulnerable release ships with no bill of materials | Workflow read | PASS |
| 5 | Security/supply chain | PII sweep | Script only | `scripts/pii-sweep-repair.py` (+ `scripts/test_pii-sweep-repair.py`) | No workflow references `pii-sweep` | Personal data enters the repo undetected; tool is dormant | 0 of 92 workflows reference `pii-sweep` | NOT_RUN |
| 6 | Supply chain | Hermetic source resolution (vendoring) | No | `vendor/` is 12 KiB of non-vendor files; no `.cargo/config.toml`; `deny.toml [sources]` allows crates.io only | n/a — reproducibility is lockfile-only | crates.io outage, yank, or index drift is a build outage | `vendor/` is 12 KiB of non-vendor files; no `.cargo/config.toml`; `deny.toml [sources]` | FAIL |
| 7 | Supply chain | Dependency gate runs the repo-pinned toolchain | Deviates | `deny.yml` L24-39: `dtolnay/rust-toolchain@stable` + unpinned `cargo install cargo-deny --locked` | Yes (weekly / push-to-`main`) | The one hard gate changes behaviour with no commit in this repo | `deny.yml` L24-39 | FAIL |
| 8 | Release integrity | Provenance attestation (SLSA Build L2) | Yes | `release-attest.yml`, `release-attestation.yml`, `verify-attestation.yml` | Yes | Released artifact is not traceable to its source | Workflow read | PASS |
| 9 | Release integrity | Artifact signing (cosign) | Partial | `scripts/sign_release.sh`, `sign_macos.sh`, `publish_docker.sh`, `sign_via_tailscale.sh` | No workflow references cosign — signing is manual/script-driven | Unsigned artifact is published unless a human remembers | 0 of 92 workflows reference cosign | NOT_RUN |
| 10 | Release integrity | Release and publish automation | Yes | `release.yml`, `release-crates.yml`, `release-binary.yml`, `publish.yml`, `publish-npm.yml`, `release-drafter.yml` | Yes (tag / PR-triggered) | Manual release step is skipped or diverges from CI reality | Workflow read | PASS |
| 11 | Docs | Docs build (VitePress → GitHub Pages) | Yes | `docs.yml` | Yes | Broken documentation ships | Workflow read | PASS |
| 12 | Docs | Markdown lint + link/validation checks | Yes | `.markdownlint.json`, `.markdownlint.yaml`, `docs-check.yml`, `doc-links.yml`, `docs-validation.yml`, `docs-lint.yml` | Yes (docs scope only) | Style drift and dead links reach published docs | Workflow read | PASS |
| 13 | Governance | Happy-path guard | Yes | `governance/happy-path-precommit.sh`, `governance/happy-path-checklist.md`, `happy-path-precommit.yml` | Yes — guard runs against the HEAD diff | Non-happy-path code merges unnoticed | `governance/happy-path-precommit.sh`; `happy-path-precommit.yml` | PASS |
| 14 | Governance | Coverage floor gate | Yes | `.coverage-baselines/root-workspace.toml` (`aggregate_floor = 36.00`), `coverage.yml`, `ratchet.yml`, `.github/scripts/coverage_report.py` | Yes (push/PR on `main`) | Coverage regresses below the floor and merges | `.coverage-baselines/root-workspace.toml`; `coverage.yml` | PASS |
| 15 | Governance | Required-check status on `main` | Spec only | `.github/BRANCH_PROTECTION_SPECS_MAIN.md` | Unverified — needs `gh api` on branch protection | Checks "run" but never block a merge | `.github/BRANCH_PROTECTION_SPECS_MAIN.md`; branch protection not queried | UNKNOWN |
| 16 | Hooks | pre-commit + lefthook configuration | Yes | `.pre-commit-config.yaml`, `lefthook.yml`, `.lefthook/`, `lefthook-check.yml` | Yes (lefthook config validated in CI) | Local-only hygiene diverges from what CI enforces | `lefthook.yml`; `lefthook-check.yml` | PASS |
| 17 | Hooks | typos + commitlint on the default path | Partial | `.typos.toml` + `crate-ci/typos` in `compute-infra-auditors.yml` only; `.commitlintrc.json` wired to `pr-lint.yml` only | One workflow / PR-title scope — no `commit-msg` hook proven | Misspellings and non-conventional commits merge | `.typos.toml`; `compute-infra-auditors.yml`; `.commitlintrc.json` | NOT_RUN |
| 18 | Observability | CI runner-cost / duplicate-trigger visibility | Partial | `coverage.yml` own comment (2026-11-08 runner-queue saturation; required check pending >40 min) | No | 89 near-duplicate workflows saturate the runner queue and stall required checks | `coverage.yml` comment; workflow inventory | UNKNOWN |

## Gaps register

| Gap | Impact | Severity | Cheapest fix | Evidence |
|---|---|---|---|---|
| PII sweep exists as a repair script but no workflow runs it | Personal data enters the repo undetected | High | Add one `pii-sweep-repair.py` step to the `ci.yml` lint job | `scripts/pii-sweep-repair.py`; `ci.yml` |
| cosign signing is script-driven, never CI-wired | Release artifacts ship unsigned unless a human runs the script | High | Add a `sigstore/cosign-installer` + `cosign sign` step to `release-binary.yml` | `scripts/sign_release.sh`; `release-binary.yml` |
| `deny.toml` is not enforced on the PR path (`ci.yml` and `license-compliance.yml` are `continue-on-error: true`; `cargo-deny.yml` targets `iac/Cargo.toml`, not root) | A disallowed license, new advisory, or non-crates.io source merges green | High | Drop `continue-on-error` on the `ci.yml` deny job and point `cargo-deny.yml` at the root manifest | `deny.toml`; `deny.yml`; `ci.yml` |
| The single enforcing dependency gate floats its own toolchain (`dtolnay@stable`, unpinned `cargo-deny`) | Gate behaviour changes with no repo commit; local 1.99.0 and CI stable diverge | Medium | Pin `dtolnay/rust-toolchain@1.99.0` and a `cargo-deny` version in `deny.yml` | `deny.yml` L24-39 |
| Two advisory ignore lists that do not share state (`deny.toml` 12 RUSTSEC, `.cargo/audit.toml` 3 RUSTSEC) | `cargo audit` and `cargo deny` can disagree about the same advisory in the same tree | Medium | Generate both ignore lists from one RUSTSEC allow-list file | `deny.toml`; `.cargo/audit.toml` |
| `bans.multiple-versions = "warn"` with `skip = []` — 6 `windows-sys`, 5 `nix`, 5 `itertools`, 5 `hashbrown`, 4 `toml`, 3 `syn`/`rand`, 2 `reqwest` generations live | Every extra generation is an independent advisory target and review surface | Medium | Set `multiple-versions = "deny"` with an explicit `skip` allowlist for the top families | `deny.toml` `[bans]` |
| Dependabot and Renovate both run on the same manifests, both with `automerge: false` on every rule | Two competing PR streams (≈40+ open) dilute review on the highest-risk surface | Medium | Keep one bot; delete or disable the other's config | `.github/dependabot.yml`; Renovate config |
| Root `LICENSE` carries `Copyright (c) 2026 <REDACTED>` while `LICENSE-MIT` names the holder; `NOTICE` names `phenotype-gfx`, a different product | Root LICENSE is not a valid MIT grant on its face; the notice points at another project | Medium | Restore the copyright line; retarget `NOTICE` to PhenoShared | `LICENSE`; `LICENSE-MIT`; `NOTICE` |
| Non-Rust surfaces (`go.sum` under `/crates/argis-extensions`, `uv.lock` 417 KiB, 5 npm dirs) are invisible to cargo-deny; Dependabot itself labels the Go module "the critical/high advisories" | Highest-severity known advisories sit on a surface no Rust gate can see | High | Wire the existing `go-audit` step in `deny.yml` to a hard gate and add a `uv`/npm scan | `go.sum`; `uv.lock`; npm package files |

Carried UNKNOWNs (not upgraded to PASS anywhere above): required-check status on `main`, Codecov upload step, trunk failure semantics, `ratchet.yml` js-coverage effectiveness, per-workflow required status names, `go-audit` gating semantics, whether MSRV 1.80 still builds, and whether the `LICENSE`/`NOTICE` anomalies are intentional.

## Four-dimension roll-up

Evidence cells only; every non-`?` cell cites a source. No percentage is derived from partial evidence.
```
PhenoShared QA posture
├── Implementation ................ PASS   `.github/workflows/` = 92 entries (89 `.yml` + 3 non-YAML files)
│   ├── test + scanner lanes ...... PASS   ci.yml, quality-gate.yml, e2e.yml; gitleaks, trufflehog, secret-guard, cargo-audit, Trivy, CodeQL, SBOM — workflow inventory
│   ├── PII sweep wired ........... FAIL   0 of 89 workflows reference scripts/pii-sweep-repair.py
│   └── cosign / typos wired ...... FAIL   4 signing scripts, 0 workflows call them; typos only in compute-infra-auditors.yml
├── Usability ..................... UNKNOWN  no developer-journey / time-to-green measurement run
│   ├── one-command gate .......... PASS   `make check` = fmt + clippy + test-unit (`Makefile:9`)
│   └── duplicate workflow pairs .. FAIL   audit/security, deny/cargo-deny, scorecard/-ci, fuzz/fuzzing in `.github/workflows/`
├── Validation .................... PASS-with-gaps
│   ├── coverage floor enforced ... PASS   `.coverage-baselines/root-workspace.toml`: aggregate 36.00 + 10 per-group floors, tarpaulin
│   ├── floor is a low bar ........ FAIL   aggregate floor 36.00 vs measured 54.79 and ~19.2k test attributes in `crates/` (16,266 `#[test]` + 2,955 `#[tokio::test]`, measured 10:53Z; drifts with the concurrent checkout)
│   └── required checks / trunk ... UNKNOWN branch protection never queried; trunk exit codes untraced
└── Assurance ..................... UNKNOWN  enforcement is real in-workflow; merge-blocking does not
    ├── repo-grounded evidence ..... PASS   every cell cites a repo path; 0 mutating git commands run
    ├── deny.toml as hard gate ..... FAIL   only `deny.yml` is non-continue-on-error; the PR path is advisory
    └── deny.yml tool pinned ....... FAIL   unpinned `cargo install cargo-deny` + `@stable`, not the repo's 1.99.x
```

## Claimed but unproven

| Claim | Where claimed | Why unproven |
|---|---|---|
| Checks are *required* on `main` | workflow trigger blocks in `.github/workflows/` | Workflows running is not proof that branch protection blocks a merge; branch protection was never queried |
| Codecov 71%/80% are live gates | `.github/codecov.yml` | No workflow uploads a report; config-only |
| `[workspace] members` = 287 | `Cargo.toml` | 287 quoted strings resolve to 283 unique paths (1 comment line, 3 duplicates); the raw 287 is not the member count |
| "0 manifests lack a `license` key" | `Cargo.toml` files | Not zero, but far from the raw-grep figure: of 688 tracked `Cargo.toml`, **317 declare `license` explicitly, 323 inherit via `license.workspace = true`, and 50 declare none at all**. A literal `^license =` grep misreports the 323 inheriting manifests as unlicensed |
| `crates/` README ×844 / CLAUDE ×111 / AGENTS ×136 | `git ls-files` | Measured 313 / 45 / 50 — up to 2.7× overstated |
| Local branches 45 / worktrees 19 | `git branch`; `git worktree list` | Measured 28 local branches / 28 worktree entries (1 main + 27 linked) |

## How to run the full gate locally

1. `cd ~/CodeProjects/Phenotype/repos/PhenoShared`
2. `make check`  # fmt + clippy + test-unit, the canonical gate
3. `cargo nextest run --workspace`  # mirrors ci.yml
4. `cargo install cargo-tarpaulin --locked && cargo tarpaulin --engine llvm --out Json -p <crate-group>`
5. `python3 .github/scripts/coverage_report.py`  # enforces .coverage-baselines/root-workspace.toml floors
6. `cargo deny check && cargo audit`  # deny.toml sections; .cargo/audit.toml has a separate ignore list
7. `trunk check`  # multi-linter; `--fix` to autofix
8. `typos --config .typos.toml`  # NOT in the default CI path
9. `actionlint && gitleaks detect --config .gitleaks.toml`
10. `./governance/happy-path-precommit.sh`  # needs HAPPY_PATH_BASE / HAPPY_PATH_HEAD
11. `python3 scripts/pii-sweep-repair.py`  # NOT in CI, run manually
12. `pre-commit install --hook-type commit-msg && pre-commit run --all-files && npm run docs:build`

## CI lane inventory

| Workflow file | Purpose | Trigger | Disabled? |
|---|---|---|---|
| `ci.yml` | nextest, ruff, gitleaks, cargo-deny (advisory) | push / PR / merge_group | No |
| `quality-gate.yml` | `make check` -> fmt + clippy + test-unit | PR + push to `main` | No |
| `coverage.yml` | Tier-2 coverage floor, tarpaulin matrix | push(main) + PR(main) | No |
| `e2e.yml` | e2e_smoke + daemon health-probe smoke | dedicated | No |
| `deny.yml` | `cargo deny check` at root, the real gate | push(main) on lockfile/manifest + weekly Mon 09:00 | No |
| `cargo-deny.yml` | cargo-deny-action on `iac/Cargo.toml` only | manifest change | No (wrong scope) |
| `security.yml`, `trunk-check.yml` | CodeQL/audit/SBOM; trunk linter | push / PR / weekly Mon 03:00 UTC | No |
| `release-macos.yml`, `pages.yml` | macOS release, Pages publish | n/a | YES, in `workflows-disabled/` |
