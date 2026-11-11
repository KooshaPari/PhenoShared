# Wave-39 scope — SessionLedger audit-v38 (391/402)

**Base:** `origin/main` @ `c065ed6` (Wave-38 closure #309–#313 + reaudit #314)  
**Method:** AgilePlus phased WBS → parallel lanes (width 5) → merge greens → reaudit → org mirror  
**Auditor posture:** conservative +1 per wave; pillar caps held without live creds/org attestation

## Audit enumeration (unpaid, machine-actionable first)

| Priority | Cluster / pillar | Gap (from SCORECARD #314)                           | Score today | W39 lane          |
| :------: | ---------------- | --------------------------------------------------- | :---------: | ----------------- |
|    P0    | C00 L8           | default-on / blocking jemalloc evidence (soft only) |      2      | w39-jemalloc-hard |
|    P0    | C07 L67          | blocking sustained fuzz beyond soft cadence         |      2      | w39-fuzz-blocking |
|    P0    | C02 L22          | envelope-crypto blocking SelfCheck (not KMS)        |      2      | w39-envelope-hard |
|    P1    | C00 L7           | broadcast/SSE daemon-graph permutation ports        |  3 (held)   | w39-daemon-graph  |
|    P1    | C04 L40          | blocking no-net for cargo-fetch security jobs       |  3 (held)   | w39-cargo-nonet   |

**Deferred (human/creds):** C04 L36 org 2FA attestation; C11 L112 Authenticode/notarization; live brew/winget publish; C06 L53 full protected-environment L3 attestation; C05 live Alertmanager/Pyroscope.

## Five lanes

| Lane              | Branch                      | Worktree            | Target                                | Score expectation      |
| ----------------- | --------------------------- | ------------------- | ------------------------------------- | ---------------------- |
| w39-jemalloc-hard | `feat/sl-w39-jemalloc-hard` | `w39-jemalloc-hard` | C00 L8 blocking jemalloc CI           | **+1** (2→3) strongest |
| w39-fuzz-blocking | `feat/sl-w39-fuzz-blocking` | `w39-fuzz-blocking` | C07 L67 blocking sustained fuzz       | **+1** (2→3)           |
| w39-envelope-hard | `feat/sl-w39-envelope-hard` | `w39-envelope-hard` | C02 L22 envelope-crypto hard evidence | **+1** (2→3)           |
| w39-daemon-graph  | `feat/sl-w39-daemon-graph`  | `w39-daemon-graph`  | C00 L7 loom broadcast/SSE ports       | held (L7 pillar max)   |
| w39-cargo-nonet   | `feat/sl-w39-cargo-nonet`   | `w39-cargo-nonet`   | C04 L40 cargo-fetch no-net policy     | held (L40 pillar max)  |

## PERT / critical path

See [`docs/ops/WAVE39_PERT.md`](docs/ops/WAVE39_PERT.md). Critical path:

1. **Scope PR** (this commit) — WBS/DAG/TRACEABILITY plan rows
2. **Parallel impl** (5 lanes, no audit file edits)
3. **Sequential merge** — rebase siblings after each `main` move
4. **Reaudit PR** — SCORECARD + lanes + GAP/TRACEABILITY/WBS closure
5. **Org mirror** — `phenotype-org-audits` (blocked while archived)

Estimated merge order (lowest conflict risk first): envelope → fuzz → jemalloc → cargo-nonet → daemon-graph.

## AgilePlus mapping

| WBS      | AgilePlus epic (SessionLedger) | Story stub                                 |
| -------- | ------------------------------ | ------------------------------------------ |
| WBS-8.58 | Lifecycle and operations (NFR) | W39 evidence packages — five machine lanes |
| WBS-8.59 | Lifecycle and operations (NFR) | W39 independent re-audit refresh           |

Run `.\scripts\agileplus-sync.ps1` after scope merge to refresh local DB listings.

## Rules (unchanged)

- **Do not edit** `audit/SCORECARD.md`, `GAP_QA_MATRIX.md`, `TRACEABILITY.json`, `WBS.md` status in feature PRs — reaudit only
- Per-worktree `CARGO_TARGET_DIR=target-w39-*`; never `git add -A` with targets inside worktree
- CHANGELOG conflicts: keep `main` Unreleased + lane bullet
- Commits: `git -c commit.gpgsign=false`; `Co-authored-by: Cursor <cursoragent@cursor.com>`

## Verify (post-impl wave)

```powershell
pwsh ./docs/ops/traceability_lint.ps1
cargo test --locked
```
