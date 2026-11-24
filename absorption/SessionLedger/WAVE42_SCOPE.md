# Wave-42 scope — SessionLedger audit-v38 (396/402)

**Base:** `origin/main` @ `2187b15` (Wave-41 re-score #338 · **396/402 · 98% A**)  
**Method:** Carry-forward Wave-41 deferred machine lanes → width-5 parallel impl → sequential merge → reaudit  
**Auditor posture:** conservative; promote soft gates and close governance gaps without creds-dependent inflation

Companion PERT: [`docs/ops/WAVE42_PERT.md`](docs/ops/WAVE42_PERT.md)

**Source:** Wave-41 deferred lanes in [`WAVE41_SCOPE.md`](WAVE41_SCOPE.md) + SCORECARD headline findings @ `2187b15`.

---

## Top unpaid gaps (396/402 → closure targets)

**6 raw points** remain across C04, C08, C11 and held pillar-max residuals. Wave-42 selects five **machine-actionable** carry-forward lanes (no creds / org attestation).

| Rank  | ID              | Class             | Gap                                                                                          | Pillar / cluster | Selected lane               |
| :---: | --------------- | ----------------- | -------------------------------------------------------------------------------------------- | ---------------- | --------------------------- |
| **1** | GAP-W41-STAB-03 | **Script safety** | `commit-signing-check.ps1` unbounded `git cat-file` + regex loop (W41 regex-bound follow-on) | C04 L34          | **w42-signing-check-bound** |
| **2** | GAP-W41-GOV-02  | **SBOM hygiene**  | CycloneDX installer unpinned; emitted SBOM not schema-validated                              | C04 L32          | **w42-sbom-validate**       |
| **3** | GAP-W41-GOV-03  | **SLSA posture**  | `slsa-protected-env` soft `continue-on-error`; not PR-blocking                               | C06 L53          | **w42-slsa-promote**        |
| **4** | GAP-W41-PERF-03 | **Alloc gates**   | `dhat` / `alloc-profile` jobs soft-only; tail alloc regressions can slip                     | C00 L8           | **w42-alloc-gate-promote**  |
| **5** | GAP-W41-DX-02   | **Viewer UX**     | Inert first-run “Open corpus…” CTA; breaks onboarding recognition                            | C09              | **w42-first-run-cta**       |

### Secondary gaps (deferred or alternate lanes)

| ID              | Gap                                                              | Notes                                     | Alternate lane          |
| --------------- | ---------------------------------------------------------------- | ----------------------------------------- | ----------------------- |
| GAP-W41-STAB-02 | Full tokio `sl-daemon` broadcast / SSE graph outside loom + TSan | C00 L7 pillar max; 8h critical path       | w42-daemon-graph-hard   |
| GAP-W41-STAB-05 | Default-on jemalloc / Windows allocator parity                   | C00 L8 residual beyond alloc-gate promote | w42-jemalloc-default-on |
| GAP-W41-DX-03   | `sl-viewer --help` minimal; onboarding doc drift                 | P1 DX                                     | w42-sl-viewer-help      |
| GAP-W41-PERF-02 | Load-smoke routes narrow; not PR-blocking                        | C08 L73                                   | w42-load-macro-gate     |
| GAP-W41-GOV-04  | Socket.dev absent                                                | SOTA supply-chain telemetry               | w42-socket-posture      |

**Deferred (human / creds / org):** C04 L36 maintainer 2FA attestation; C04 L40 live rootless-only runner matrix; C06 L53 full L3 Environment attestation; C06 L59 live signed-commits attestation; C11 L112 Authenticode/notarization; live brew/winget; `phenotype-org-audits` org mirror (403/403).

---

## Five parallel implementation lanes (width 5)

Cross-pillar selection: two P0 script/governance hardening, two soft→blocking gate promotions, one P1 viewer DX polish.

| Priority | Lane                    | Branch                            | Worktree                  | Target                                                                                    | Score expectation                          |
| :------: | ----------------------- | --------------------------------- | ------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------ |
|  **P0**  | w42-signing-check-bound | `feat/sl-w42-signing-check-bound` | `w42-signing-check-bound` | Bound `git cat-file` / regex loops in `commit-signing-check.ps1`; `-SelfCheck` green      | held (C04 evidence depth)                  |
|  **P0**  | w42-sbom-validate       | `feat/sl-w42-sbom-validate`       | `w42-sbom-validate`       | Pin `cargo-cyclonedx` installer version/checksum; validate emitted SBOM JSON schema in CI | held or **+1** C04 L32                     |
|  **P1**  | w42-slsa-promote        | `feat/sl-w42-slsa-promote`        | `w42-slsa-promote`        | Promote `slsa-protected-env-check.ps1` from soft to blocking on PRs                       | held (C06 L53 residual attestation unpaid) |
|  **P1**  | w42-alloc-gate-promote  | `feat/sl-w42-alloc-gate-promote`  | `w42-alloc-gate-promote`  | Promote `alloc-profile` / dhat smoke from `continue-on-error` to blocking                 | held or **+1** C00 L8                      |
|  **P1**  | w42-first-run-cta       | `feat/sl-w42-first-run-cta`       | `w42-first-run-cta`       | Wire first-run “Open corpus…” CTA to corpus picker / docs quick-start                     | held (C09 UX polish)                       |

**Not selected this wave (carry-forward):** w42-daemon-graph-hard (8h), w42-jemalloc-default-on, w42-sl-viewer-help, w42-load-macro-gate, w42-org-mirror.

---

## Score expectations

| Outcome                             |    Raw score    |   Grade   | Notes                                                    |
| ----------------------------------- | :-------------: | :-------: | -------------------------------------------------------- |
| Baseline (Wave-41)                  |     396/402     |   98% A   | SCORECARD @ `2187b15`                                    |
| W42 all lanes merged (conservative) | **396–398/402** | **98% A** | Most lanes deepen evidence at pillar max                 |
| Optimistic (+1–2 accepted)          |     398/402     |   99% A   | Requires auditor buy-in on L32 SBOM / L8 alloc promotion |

---

## Cross-reference: Wave-41 patterns

| Wave-41 lane          | Pattern                      | W42 carry-forward                              |
| --------------------- | ---------------------------- | ---------------------------------------------- |
| w41-check-regex-bound | Line-scanner YAML extraction | Extend to `commit-signing-check.ps1` IO bounds |
| w41-source-provenance | TRACEABILITY wrapper closure | SBOM schema validation closes C04 L32 gap      |
| w41-ci-timeout        | Workflow resilience          | SLSA/alloc promotion removes soft bypass       |
| w41-daemon-url-unify  | Viewer UX bugfix             | First-run CTA completes onboarding loop        |

---

## PERT / critical path

See [`docs/ops/WAVE42_PERT.md`](docs/ops/WAVE42_PERT.md).

**Merge order (lowest conflict risk):** signing-check-bound → sbom-validate → slsa-promote → alloc-gate-promote → first-run-cta (viewer crates last).

---

## AgilePlus mapping

| WBS stub | Epic               | Story                                            |
| -------- | ------------------ | ------------------------------------------------ |
| WBS-8.64 | Lifecycle / NFR    | W42 consolidated scope — five cross-pillar lanes |
| WBS-8.65 | Security (C04)     | Signing-check script bounds                      |
| WBS-8.66 | Security (C04)     | SBOM schema validation                           |
| WBS-8.67 | Supply chain (C06) | SLSA protected-env gate promotion                |
| WBS-8.68 | Architecture (C00) | Alloc-profile gate promotion                     |
| WBS-8.69 | Viewer UX (C09)    | First-run corpus CTA                             |

Run `.\scripts\agileplus-sync.ps1` after scope merge.

---

## Rules (unchanged)

- **Do not edit** `audit/SCORECARD.md`, `docs/ops/GAP_QA_MATRIX.md`, `TRACEABILITY.json`, `WBS.md` status in feature PRs — reaudit only
- Per-worktree `CARGO_TARGET_DIR=target-w42-*`; never `git add -A` with targets inside worktree
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
