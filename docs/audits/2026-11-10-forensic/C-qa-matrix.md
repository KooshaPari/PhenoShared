# C — QA / Quality Gate Matrix (PhenoShared)

Repo: `/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared`
Audited: 2026-11-09 (lane C2, forensic pass)
Method: read-only inspection of `.github/workflows/`, repo-root tool configs, `governance/`, and CI scripts. No CI run was executed; every "Enforced in CI" cell is evidence of a workflow that *runs* the control, not proof that the check is **required** on `main` (see "Unproven" below).

## Scale

`.github/workflows/` holds **92 entries** — 89 workflow YAMLs plus `README.md`, `STATUS.md`, `naming-conventions.sh`. A further `pages.yml` and `release-macos.yml` sit in `.github/workflows-disabled/`.

---

## Matrix

| Control | Exists | Where | Enforced in CI | Verdict |
|---|---|---|---|---|
| Unit tests (Rust) | Yes | `ci.yml` (cargo nextest), `quality-gate.yml` (`make check` → `fmt clippy test-unit`), `reusable-test.yml` | Yes — `ci.yml` on push/PR/merge_group; `quality-gate.yml` on PR+push to `main` | PASS |
| Integration tests | Yes | `reusable-test.yml`, `iac-rust.yml`, `ffi-ci.yml`, `libs-activation-ci.yml`, `ai-testing-orchestration.yml` (pytest), `fabric-integration-tests` crate | Yes | PASS |
| E2E tests | Yes | `e2e.yml` — `cargo test -p fabric-integration-tests --test e2e_smoke --no-fail-fast --locked`; daemon-binary smoke job (start daemon, `nc` health probe, stop) | Yes (dedicated workflow) | PASS |
| Python tests | Yes | `reusable-test.yml`, `ai-testing-orchestration.yml` (pytest), `ci.yml` python job (ruff lint + format) | Yes | PASS |
| Browser E2E (Playwright) | Yes | `reusable-a11y.yml`, `ai-testing-orchestration.yml` | Yes | PASS |
| Coverage floor | Yes | `.coverage-baselines/root-workspace.toml` — `aggregate_floor = 36.00`; 10 per-crate-group floors (agileplus 58.93, device-media 60.09, fabric 44.30, focus 76.49, integrations 41.87, pheno-core 47.13, runtime-hosts 51.75, sharecli-core 61.43, sharecli-surface 63.33, substrate 61.01). Legacy `.coverage-baseline` = 100. `coverage.yml` ("Coverage Gate (Tier-2)"), `fr-coverage.yml`, `ratchet.yml`, `.github/scripts/coverage_report.py` | Yes — `coverage.yml` on push(main) + PR(main); floor enforced via `cargo tarpaulin` matrix | PASS (floor is real but **low**: 36% aggregate) |
| Codecov status gate | Yes | `.github/codecov.yml` — project target 71%, patch target 80%, iac 60%, threshold 1% | Config only — **no workflow step was found that uploads to Codecov** | UNKNOWN / WEAK |
| clippy | Yes | `reusable-lint.yml` (`cargo clippy --workspace --all-targets -- -D warnings` when `fail-on-warnings=true`), `quality-gate.yml` (`make check`), `iac-rust.yml`, `tf-ci.yml`, `perf-core-ci.yml`, `windows-browser-tree.yml` | Yes | PASS |
| rustfmt / `cargo fmt --check` | Yes | `Makefile: fmt` → `cargo fmt --all --check`; `reusable-lint.yml`; `quality-gate.yml` | Yes | PASS |
| trunk (multi-linter) | Yes | `trunk.yaml`, `.trunk/`, `trunk-check.yml` (PR + push + weekly Mon 03:00 UTC cron) | Yes — no `continue-on-error` observed in the trigger/step region | PASS |
| typos | Partial | `.typos.toml`, `_typos.toml` configs; `crate-ci/typos@…` action used in `compute-infra-auditors.yml` only | Weak — **not** in `ci.yml`/`quality-gate.yml`/`trunk-check.yml`; no typos plugin under `.trunk/plugins` (only `trunk`) | WEAK |
| markdownlint | Yes | `.markdownlint.json`, `.markdownlint.yaml`; `docs-check.yml` | Yes (docs scope only) | PASS |
| commitlint | Partial | `.commitlintrc.json`, `.commitlintrc.yml`; `pr-lint.yml` = "Lint PR title" | PR-title scope only — **no commit-msg hook** proven for commit messages | WEAK |
| gitleaks | Yes | `.gitleaks.toml` (extends upstream ruleset, allowlists only fixture secrets); `security.yml`, `ci.yml` | Yes | PASS |
| trufflehog | Yes | `trufflehog.yml` | Yes (dedicated workflow) | PASS |
| Secret guard (custom) | Yes | `secret-guard.yml` → `scripts/workflow-action-guard.py`; GitGuardian config `.github/gitguardian.yaml`; `scripts/retained-history-secret-scan.py` | Yes | PASS |
| cargo-audit | Yes | `security.yml` (Dependency audit job), `security-scan.yml`, `ffi-ci.yml` | Yes | PASS |
| cargo-deny | Yes | `deny.toml`; `cargo-deny.yml`, `deny.yml`, `ci.yml` (job "Cargo Deny (Advisories + Licenses)"), `license-compliance.yml` | Yes | PASS |
| cargo-semver-checks | Yes | `cargo-semver-checks.yml` | Yes | PASS |
| cargo-machete | Yes | `cargo-machete.yml` (unused-dependency detection) | Yes | PASS |
| Trivy (container/FS scan) | Yes | `audit.yml` ("Security Guard") → `aquasecurity/trivy-action` | Yes | PASS |
| CodeQL | Yes | `codeql.yml` + `.github/codeql/`; `security.yml` CodeQL (rust) job | Yes | PASS |
| scorecard (OpenSSF) | Yes | `scorecard.yml`, `scorecard-ci.yml`, `compute-infra-auditors.yml` | Yes | PASS |
| SBOM | Yes | `sbom.yml`, `sbom-monthly.yml`, `security.yml` (CycloneDX via `cargo-cyclonedx`, artifact upload) | Yes | PASS |
| syft | No | no reference found in `.github/` | n/a | GAP (CycloneDX via cargo-cyclonedx covers the need) |
| cosign signing | Partial | `scripts/sign_release.sh`, `scripts/sign_macos.sh`, `scripts/publish_docker.sh`, `scripts/sign_via_tailscale.sh` | **No workflow references cosign** — signing is manual/script-driven, not CI-wired | WEAK |
| Provenance attestation | Yes | `release-attest.yml` → `actions/attest-build-provenance` (attestations: write); `release-attestation.yml` (SLSA Build L2); `verify-attestation.yml` | Yes | PASS |
| Docs build | Yes | `docs.yml` (VitePress `npm run docs:build` → GitHub Pages); `docs-check.yml`, `docs-validation.yml`, `doc-links.yml`, `docs-lint.yml` | Yes | PASS |
| actionlint | Yes | `.github/actionlint.yaml` (self-hosted runner labels); `docs-lint.yml`, `scorecard-ci.yml` | Yes | PASS |
| **PII sweep** | Script only | `scripts/pii-sweep-repair.py`, `scripts/test_pii_sweep_repair.py` | **No workflow references `pii-sweep`** — tooling exists but is not wired to CI | **GAP** |
| Happy-path guard | Yes | `governance/happy-path-precommit.sh` (`HAPPY_PATH_FAIL_ON=block` default; R3 big-constant allowlist), `governance/happy-path-checklist.md`, `governance/test-happy-path-allowlist.sh`, `governance/test-happy-path-claims.sh` | Yes — `happy-path-precommit.yml` runs the guard against the HEAD diff | PASS |
| Pre-commit hooks | Yes | `.pre-commit-config.yaml` (trailing-ws, EOF, check-yaml/json/toml/xml, merge-conflict, large-file, detect-private-key, no-commit-to-branch, ruff, ruff-format, mypy); `lefthook.yml` + `.lefthook/`; `lefthook-check.yml` validates the lefthook config | Yes (lefthook config validated in CI) | PASS |
| Release automation | Yes | `release.yml`, `release-crates.yml`, `release-binary.yml`, `publish.yml` (npm), `publish-npm.yml`, `publish-pypi.yml`, `release-promptscrape.yml`, `release-drafter.yml`, `release-landing-packages.yml` | Yes (tag/PR-triggered) | PASS |
| Mutation testing | Yes | `mutation.yml` | Yes | PASS |
| Fuzzing | Yes | `fuzz.yml`, `fuzzing.yml` | Yes | PASS |
| Flaky-test detection | Yes | `flaky-tests.yml` | Yes | PASS |
| Spec / traceability gates | Yes | `spec-validation.yml`, `traceability-gate.yml`, `policy-gate.yml`, `qwen35-policy-gate.yml`, `governance.yml` | Yes | PASS |
| Naming / conventions | Yes | `naming-conventions.yml`, `conventions.yml`, `branch-name.yml`, `dedup-check.yml`, `cargo-machete.yml` | Yes | PASS |

---

## Unproven (UNKNOWN, not failed)

1. **Required-check status on `main`.** `.github/BRANCH_PROTECTION_SPECS_MAIN.md` is a *specs/main SSOT policy* document, not a list of required CI checks. Whether `Quality Gate`, `Coverage Gate (Tier-2)`, `Trunk Check`, `Security`, `cargo-deny` etc. are actually **required** in GitHub branch protection was not verified (needs `gh api` on branch protection — out of lane scope). Treat "Enforced in CI" as *runs*, not *blocks merge*.
2. **Codecov upload step.** `.github/codecov.yml` exists with real targets (71% / 80% patch) but no workflow step uploading a report was located in the sampled workflows. Coverage gating is nonetheless independently proven via `coverage.yml` + tarpaulin floors.
3. **Trunk failure semantics.** `trunk-check.yml` was read only for trigger/steps; the trunk action's exit-code handling was not confirmed end-to-end.
4. **`ratchet.yml` js-coverage job.** The file's own comment documents that it previously could not measure anything (bun workspace + `npm ci` failure on `workspace:*`). Current effectiveness UNKNOWN without a run.
5. **Per-workflow required status names** were not cross-checked against live GitHub check-runs.

---

## Gaps (real, ordered by risk)

1. **PII sweep is not in CI.** `scripts/pii-sweep-repair.py` + its test exist, but no workflow references them. A repair script with no gate is a dormant tool.
2. **cosign signing is manual.** Four signing scripts exist; zero workflows invoke them. Release artifacts are signed only if a human remembers to run them.
3. **typos is scoped to one workflow.** `crate-ci/typos` runs only in `compute-infra-auditors.yml`, and typos is not a trunk plugin. Misspellings outside that workflow's scope pass unblocked.
4. **commitlint covers PR titles, not commit messages.** `.commitlintrc.*` exists but the only wiring is `pr-lint.yml`. Conventional-commit enforcement on the commit itself is unproven.
5. **Coverage floor is 36% aggregate.** The ratchet design and per-group floors are well documented and legitimate, but a 36% aggregate floor is a low bar for a 16k-`#[test]` workspace. Codecov's 71%/80% targets may be aspirational only (see Unproven #2).
6. **No PII / secret-in-generated-content gate** beyond the secret scanners (gitleaks/trufflehog/secret-guard), which look for credentials, not personal data.
7. **Minor duplication in the security surface.** `audit.yml` and `security.yml`, `deny.yml` and `cargo-deny.yml`, `scorecard.yml` and `scorecard-ci.yml`, `fuzz.yml` and `fuzzing.yml` are near-duplicate pairs; combined with 89 workflows this raises maintenance/runner-cost risk (see `coverage.yml`'s own comment about a 2026-11-08 runner-queue saturation from duplicated triggers).
8. **`workflows-disabled/`** still holds `release-macos.yml` — a release path that exists but is switched off, with no dated reason visible.

---

## Run locally

**Rust gate (the canonical one — `make check` = fmt + clippy + unit tests):**
```bash
cd ~/CodeProjects/Phenotype/repos/PhenoShared
make check                      # fmt + clippy + test-unit
cargo fmt --all --check
cargo clippy --workspace --all-targets -- -D warnings
cargo nextest run --workspace   # mirrors ci.yml
```

**Coverage floor (tarpaulin, same instrument as CI):**
```bash
cargo install cargo-tarpaulin --locked
cargo llvm-cov --version || rustup component add llvm-tools-preview
# per crate group, matching .coverage-baselines/root-workspace.toml
cargo tarpaulin --engine llvm --out Json -p <crate-group>
python3 .github/scripts/coverage_report.py    # compares against the TOML floors
```

**Static analysis / supply chain:**
```bash
cargo deny check               # advisories + licenses (deny.toml)
cargo audit                    # RustSec advisories
trunk check                    # multi-linter (trunk.yaml); trunk check --fix to autofix
typos --config .typos.toml     # NOT in the default CI path — run it explicitly
actionlint                     # workflow lint (.github/actionlint.yaml)
gitleaks detect --config .gitleaks.toml
```

**Docs:**
```bash
npm install --legacy-peer-deps && npm run docs:build     # matches docs.yml
npx markdownlint-cli2 "**/*.md"                          # .markdownlint.json
```

**Governance guards:**
```bash
./governance/happy-path-precommit.sh                     # needs HAPPY_PATH_BASE/HAPPY_PATH_HEAD
./governance/test-happy-path-allowlist.sh
./governance/test-happy-path-claims.sh
python3 scripts/pii-sweep-repair.py                      # NOT in CI — run manually
```

**Hooks:**
```bash
pre-commit install && pre-commit install --hook-type commit-msg
pre-commit run --all-files
lefthook run                                    # validates against lefthook-check.yml
```

**Release:**
```bash
./scripts/sign_release.sh                       # cosign — NOT invoked by any workflow
```

---

## Evidence notes

- Test-file count via pattern `(^|/)tests?/|\.test\.|_test\.(rs|py|go)$|test_.*\.py$` = **3622 tracked files**, but this count is inflated by the `absorption/` and `_archived/` trees vendored in the repo. The in-tree Rust `#[test]` count under `crates/` alone is **16289** — these are the numbers a coverage floor of 36% applies to.
- Coverage provenance is documented in-file: floors were measured 2026-11-09 from cargo-tarpaulin run `42605873709` on `ubuntu-24.04`, stable toolchain, `llvm-tools-preview`.
- `coverage.yml` documents a real incident: duplicated push+pull_request triggers saturated the hosted-runner queue on 2026-11-08, leaving the required "Root workspace coverage" check pending >40 min on open PRs.
