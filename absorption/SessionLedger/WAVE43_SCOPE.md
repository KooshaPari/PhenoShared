# Wave-43 scope — SessionLedger audit-v38 (396/402)

**Base:** `origin/main` @ `5598dfa` (Wave-42 re-score #345 · **396/402 · 98% A**)  
**Method:** Carry-forward Wave-42 deferred machine lanes → width-5 parallel impl → sequential merge → reaudit  
**Auditor posture:** conservative; deepen stability/DX/eval evidence without creds-dependent inflation

Companion PERT: [`docs/ops/WAVE43_PERT.md`](docs/ops/WAVE43_PERT.md)

**Source:** Wave-42 deferred lanes in [`WAVE42_SCOPE.md`](WAVE42_SCOPE.md) + SCORECARD headline findings @ `5598dfa`.

---

## Top unpaid gaps (396/402 → closure targets)

**6 raw points** remain across C04, C08, C11 and held pillar-max residuals. Wave-43 selects five **machine-actionable** carry-forward lanes (no creds / org attestation).

| Rank  | ID              | Class                      | Gap                                                              | Pillar / cluster | Selected lane               |
| :---: | --------------- | -------------------------- | ---------------------------------------------------------------- | ---------------- | --------------------------- |
| **1** | GAP-W42-STAB-01 | **Concurrency depth**      | Full tokio `sl-daemon` broadcast / SSE graph outside loom + TSan | C00 L7           | **w43-daemon-graph-hard**   |
| **2** | GAP-W42-STAB-02 | **Allocator policy**       | Default-on jemalloc / Windows allocator parity beyond hard gate  | C00 L8           | **w43-jemalloc-default-on** |
| **3** | GAP-W42-PERF-01 | **Load eval**              | `load-smoke` routes narrow; not PR-blocking                      | C08 L73          | **w43-load-macro-gate**     |
| **4** | GAP-W42-DX-01   | **CLI / viewer DX**        | `sl-viewer --help` minimal; onboarding doc drift                 | C01 / C09        | **w43-sl-viewer-help**      |
| **5** | GAP-W42-GOV-01  | **Supply-chain telemetry** | Socket.dev absent from PR security posture                       | C06              | **w43-socket-posture**      |

### Secondary gaps (deferred or alternate lanes)

| ID              | Gap                                            | Notes                          | Alternate lane          |
| --------------- | ---------------------------------------------- | ------------------------------ | ----------------------- |
| GAP-W42-STAB-03 | C04 L32 SBOM pillar residual after schema gate | May need auditor buy-in for +1 | w43-sbom-pillar-close   |
| GAP-W41-DX-04   | Fluent i18n migration incomplete               | C01 L16; large surface         | w43-fluent-viewer-stub  |
| GAP-W41-STAB-04 | Export/search skip summary                     | P2 CLI polish                  | w43-export-skip-summary |

**Deferred (human / creds / org):** C04 L36 maintainer 2FA attestation; C04 L40 live rootless-only runner matrix; C06 L53 full L3 Environment attestation; C06 L59 live signed-commits attestation; C11 L112 Authenticode/notarization; live brew/winget; `phenotype-org-audits` org mirror (403/403).

---

## Five parallel implementation lanes (width 5)

Cross-pillar selection: one long stability lane, two C00 allocator/concurrency depth lanes, one C08 eval promotion, one DX + one supply-chain telemetry lane.

| Priority | Lane                    | Branch                            | Worktree                  | Target                                                                                | Score expectation                |
| :------: | ----------------------- | --------------------------------- | ------------------------- | ------------------------------------------------------------------------------------- | -------------------------------- |
|  **P0**  | w43-daemon-graph-hard   | `feat/sl-w43-daemon-graph-hard`   | `w43-daemon-graph-hard`   | Port full tokio `sl-daemon` broadcast/SSE graph into blocking permutation coverage    | held (C00 L7 already pillar max) |
|  **P1**  | w43-jemalloc-default-on | `feat/sl-w43-jemalloc-default-on` | `w43-jemalloc-default-on` | Default-on jemalloc feature + Windows parity policy/docs                              | held or **+1** C00 L8            |
|  **P1**  | w43-load-macro-gate     | `feat/sl-w43-load-macro-gate`     | `w43-load-macro-gate`     | Promote macro load-smoke routes to blocking PR gate                                   | held or **+1** C08 L73           |
|  **P1**  | w43-sl-viewer-help      | `feat/sl-w43-sl-viewer-help`      | `w43-sl-viewer-help`      | Expand `sl-viewer --help` / `--version`; document `SL_DAEMON_URL`, `FORGE_DB`         | held (C01/C09 DX)                |
|  **P2**  | w43-socket-posture      | `feat/sl-w43-socket-posture`      | `w43-socket-posture`      | Socket.dev PR scan SelfCheck + docs anchor (no live org token required for SelfCheck) | held (C06 telemetry depth)       |

**Not selected this wave (carry-forward):** w43-fluent-viewer-stub, w43-export-skip-summary, w43-sbom-pillar-close, w43-org-mirror.

---

## Score expectations

| Outcome                             |    Raw score    |   Grade   | Notes                                                  |
| ----------------------------------- | :-------------: | :-------: | ------------------------------------------------------ |
| Baseline (Wave-42)                  |     396/402     |   98% A   | SCORECARD @ `5598dfa`                                  |
| W43 all lanes merged (conservative) | **396–398/402** | **98% A** | Most lanes deepen evidence at pillar max               |
| Optimistic (+1–2 accepted)          |     398/402     |   99% A   | Requires auditor buy-in on L8 jemalloc / L73 load gate |

---

## Cross-reference: Wave-42 patterns

| Wave-42 lane            | Pattern                      | W43 carry-forward                              |
| ----------------------- | ---------------------------- | ---------------------------------------------- |
| w42-alloc-gate-promote  | Soft→blocking gate promotion | load-macro-gate for C08                        |
| w42-first-run-cta       | Viewer onboarding polish     | sl-viewer-help completes DX loop               |
| w42-slsa-promote        | Security workflow blocking   | socket-posture PR telemetry                    |
| w42-signing-check-bound | Script bounds / SelfCheck    | daemon-graph-hard extends concurrency evidence |

---

## PERT / critical path

See [`docs/ops/WAVE43_PERT.md`](docs/ops/WAVE43_PERT.md).

**Merge order (lowest conflict risk):** socket-posture → load-macro-gate → jemalloc-default-on → sl-viewer-help → daemon-graph-hard (daemon/loom crates last).

---

## AgilePlus mapping

| WBS stub | Epic                | Story                                            |
| -------- | ------------------- | ------------------------------------------------ |
| WBS-8.66 | Lifecycle / NFR     | W43 consolidated scope — five cross-pillar lanes |
| WBS-8.67 | Architecture (C00)  | Daemon tokio broadcast/SSE graph hardening       |
| WBS-8.68 | Architecture (C00)  | Jemalloc default-on policy                       |
| WBS-8.69 | Eval coverage (C08) | Load-macro PR gate                               |
| WBS-8.70 | CI / DX (C01)       | sl-viewer help + env docs                        |
| WBS-8.71 | Supply chain (C06)  | Socket.dev posture SelfCheck                     |

Run `.\scripts\agileplus-sync.ps1` after scope merge.

---

## Rules (unchanged)

- **Do not edit** `audit/SCORECARD.md`, `docs/ops/GAP_QA_MATRIX.md`, `TRACEABILITY.json`, `WBS.md` status in feature PRs — reaudit only
- Per-worktree `CARGO_TARGET_DIR=target-w43-*`; never `git add -A` with targets inside worktree
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
