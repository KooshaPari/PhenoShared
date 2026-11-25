# Wave-41 scope — SessionLedger audit-v38 (396/402)

**Base:** `origin/main` @ `789c7f3` (Wave-40 re-score #329 · **396/402 · 98% A**)  
**Method:** Consolidate stability / DX·UX / governance / perf audits → width-5 parallel lanes → sequential merge → reaudit  
**Auditor posture:** conservative; most lanes deepen evidence at pillar max rather than raw score inflation

Companion PERT: [`docs/ops/WAVE41_PERT.md`](docs/ops/WAVE41_PERT.md)

**Source audits (synthesized):**

| Audit       | Artifact                                          |
| ----------- | ------------------------------------------------- |
| Stability   | `w41-stability-audit/WAVE41_STABILITY_SCOPE.md`   |
| DX/UX       | `w41-dx-ux-audit/WAVE41_DX_UX_SCOPE.md`           |
| Governance  | `w41-governance-audit/WAVE41_GOVERNANCE_SCOPE.md` |
| Performance | `w41-perf-audit/WAVE41_PERF_SCOPE.md`             |

---

## Top unpaid gaps (396/402 → closure targets)

Consolidated from SCORECARD headline findings + four Wave-41 audits. **6 points** remain across C04, C08, C11 and held pillar-max residuals.

| Rank  | ID              | Class                  | Gap                                                                                                                                                             | Pillar / cluster | Selected lane             |
| :---: | --------------- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------------------- |
| **1** | GAP-W41-DX-01   | **Viewer UX bug**      | Live Feed hardcodes `localhost:9001`; daemon, Search, Replay, `.env.example`, runbook use `:8080` — tab fails on default `make dev`                             | C09 (UX)         | **w41-daemon-url-unify**  |
| **2** | GAP-W41-STAB-01 | **CI hang**            | Primary workflows (`ci.yml`, `security.yml`, `qgate.yml`, `commit-signing.yml`) lack `timeout-minutes`; stuck `cargo install` / property reruns burn 6h default | C01 / C07        | **w41-ci-timeout**        |
| **3** | GAP-W41-STAB-04 | **CI ReDoS**           | `sandbox-boundary-check.ps1` and `oci-cosign-verify.ps1` use lazy `(?ms)...*?` YAML extraction — catastrophic backtracking as workflows grow (W40 lesson)       | C04 L40          | **w41-check-regex-bound** |
| **4** | GAP-W41-GOV-01  | **Traceability chain** | `TRACEABILITY.json` lists `tests/source_provenance.rs` but file **missing** at `789c7f3`; C06 L59 wrapper gap                                                   | C06 L59          | **w41-source-provenance** |
| **5** | GAP-W41-PERF-01 | **Provisional p95**    | `perf-baseline.json` p95 values ≈ `mean_ns × 1.15` (synthetic); tail regressions can slip under loose ceilings                                                  | C00 L6 / C08 L74 | **w41-p95-baseline**      |

### Secondary gaps (deferred or alternate lanes)

| ID              | Gap                                                                   | Notes                            | Alternate lane            |
| --------------- | --------------------------------------------------------------------- | -------------------------------- | ------------------------- |
| GAP-W41-STAB-02 | Full tokio `sl-daemon` broadcast / SSE graph outside loom + TSan      | C00 L7 pillar max; evidence-only | w41-daemon-graph-hard     |
| GAP-W41-STAB-03 | `commit-signing-check.ps1` unbounded `git cat-file` + regex loop      | Overlaps regex-bound theme       | w41-signing-check-bound   |
| GAP-W41-STAB-05 | jemalloc / alloc soft jobs `continue-on-error`; Windows parity unpaid | C00 L8 residual                  | w41-alloc-regression-hard |
| GAP-W41-GOV-02  | SBOM schema validation + pinned `cargo-cyclonedx`                     | C04 L32                          | w41-sbom-validate         |
| GAP-W41-GOV-03  | SLSA protected-env + isolation soft → block                           | C06 L53 residual                 | w41-slsa-promote          |
| GAP-W41-GOV-04  | Socket.dev absent                                                     | SOTA supply-chain telemetry      | w41-socket-posture        |
| GAP-W41-DX-02   | Inert first-run “Open corpus…” CTA                                    | P1 viewer polish                 | w41-first-run-cta         |
| GAP-W41-DX-03   | `sl-viewer --help` minimal; onboarding doc drift                      | P1 DX                            | w41-sl-viewer-help        |
| GAP-W41-PERF-02 | Load-smoke routes narrow; not PR-blocking                             | C08 L73                          | w41-load-macro-gate       |
| GAP-W41-PERF-03 | dhat / alloc-profile soft-only                                        | C00 L8                           | w41-alloc-gate-promote    |

**Deferred (human / creds / org):** C04 L36 maintainer 2FA attestation; C04 L40 live rootless-only runner matrix; C06 L53 full L3 Environment attestation; C06 L59 live signed-commits attestation; C11 L112 Authenticode/notarization; live brew/winget; `phenotype-org-audits` org mirror (404/403).

---

## Five parallel implementation lanes (width 5)

Cross-pillar selection: one P0 DX bug, two P0 stability/governance hardening, one W40 regex lesson, one perf baseline refresh.

| Priority | Lane                  | Branch                          | Worktree                | Target                                                                                                                    | Score expectation         |
| :------: | --------------------- | ------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------- |
|  **P0**  | w41-daemon-url-unify  | `feat/sl-w41-daemon-url`        | `w41-daemon-url-unify`  | Single runtime daemon base URL module; fix Live Feed `:9001` → default `:8080`; align Search/Replay/LiveFeed + error copy | held (UX bugfix)          |
|  **P0**  | w41-ci-timeout        | `feat/sl-w41-ci-timeout`        | `w41-ci-timeout`        | `timeout-minutes` on `ci.yml`, `security.yml`, `qgate.yml`, `commit-signing.yml` jobs                                     | held (C01 ops resilience) |
|  **P1**  | w41-check-regex-bound | `feat/sl-w41-check-regex-bound` | `w41-check-regex-bound` | Line-scanner YAML extraction (no lazy `(?ms).*?`) in sandbox + oci-cosign scripts                                         | held (C04 evidence depth) |
|  **P1**  | w41-source-provenance | `feat/sl-w41-source-provenance` | `w41-source-provenance` | Add missing `tests/source_provenance.rs` cargo wrapper; align with `source-provenance-check.ps1 -SelfCheck`               | held or **+1** C06 L59    |
|  **P1**  | w41-p95-baseline      | `feat/sl-w41-p95-baseline`      | `w41-p95-baseline`      | Refresh `perf-baseline.json` p95 from Criterion `sample.json`; optional `p95_source` metadata                             | held (C08 L74 evidence)   |

**Not selected this wave (carry-forward):** w41-daemon-graph-hard (8h critical path), w41-signing-check-bound, w41-sbom-validate, w41-slsa-promote, w41-first-run-cta, w41-org-mirror.

---

## Score expectations

| Outcome                                    |    Raw score    |   Grade   | Notes                                    |
| ------------------------------------------ | :-------------: | :-------: | ---------------------------------------- |
| Baseline (Wave-40)                         |     396/402     |   98% A   | SCORECARD @ `789c7f3`                    |
| W41 all lanes merged (conservative)        | **396–398/402** | **98% A** | Most lanes deepen evidence at pillar max |
| Optimistic (+1–2 governance/perf accepted) |     398/402     |   99% A   | Requires auditor buy-in on L59 / L74     |

---

## Cross-reference: Wave-40 patterns

| Wave-40 lane          | Pattern            | W41 carry-forward                       |
| --------------------- | ------------------ | --------------------------------------- |
| w40-eval-repro        | Manifest hard sync | Baseline for perf lane eval-repro gate  |
| w40-signing-readiness | Signing hard gate  | Regex-bound extends script safety       |
| w40-rootless-nonet    | Scaffold only      | Live runner matrix still human          |
| w40-daemon-tokio      | Partial loom ports | Full graph → deferred daemon-graph-hard |

---

## PERT / critical path

See [`docs/ops/WAVE41_PERT.md`](docs/ops/WAVE41_PERT.md).

**Merge order (lowest conflict risk):** ci-timeout → check-regex-bound → source-provenance → p95-baseline → daemon-url-unify (viewer crates last).

---

## AgilePlus mapping

| WBS stub | Epic                | Story                                            |
| -------- | ------------------- | ------------------------------------------------ |
| WBS-8.64 | Lifecycle / NFR     | W41 consolidated scope — five cross-pillar lanes |
| WBS-8.65 | Viewer UX (C09)     | Daemon URL unification                           |
| WBS-8.66 | Supply chain (C06)  | Source-provenance test wrapper                   |
| WBS-8.67 | Eval coverage (C08) | Measured p95 baseline refresh                    |

Run `.\scripts\agileplus-sync.ps1` after scope merge.

---

## Rules (unchanged)

- **Do not edit** `audit/SCORECARD.md`, `docs/ops/GAP_QA_MATRIX.md`, `TRACEABILITY.json`, `WBS.md` status in feature PRs — reaudit only
- Per-worktree `CARGO_TARGET_DIR=target-w41-*`; never `git add -A` with targets inside worktree
- CHANGELOG Unreleased + lane bullet on feature PRs
- Commits: `git -c commit.gpgsign=false`; `Co-authored-by: Cursor <cursoragent@cursor.com>`

## Verify (post-impl wave)

```powershell
pwsh ./docs/ops/traceability_lint.ps1
cargo test --locked
pwsh ./scripts/flake-tracker-check.ps1
cargo test -p sl-viewer --locked
./scripts/bench-gate.ps1 -SelfCheck
```
