# Closure DAG — PhenoShared, 2026-10-30

**Purpose:** make the remaining work *blind-closable*. The operator may terminate
this session at any moment. Every node is designed so that a kill lands on a
committed, no-worse-than-baseline state.

## Kill-safety contract

1. Every leaf ends with a commit (or a "no change needed" entry in this file).
2. No leaf may leave `main` worse than the recorded baseline below.
3. This file is updated **in the same commit** as the work it describes.
4. Any leaf projected to exceed ~10 minutes unattended is split before starting.
5. No leaf depends on chat context that a fresh agent could not read here.

## Verified baseline (do not re-derive)

| Item | Value | Source |
|---|---|---|
| Repo | `github.com/KooshaPari/PhenoShared` | `git remote -v` |
| Verified green commit | `5b67921f` (CI run `41070566146`) | GH Actions API |
| Go gate | 13 modules + `Go Module Registry` all **success** | run `41070566146` |
| `Cargo Deny (Advisories + Licenses)` | **failure** (pre-existing) | same run |
| `Coverage Gate (Tier-2)` | **failure** (pre-existing, failing ≥6 prior commits) | workflow history |
| Open PRs | 27 (12 CONFLICTING, 15 MERGEABLE) | `gh pr list` |
| Local branches | 25 (1 merged into main) | `git branch` |
| Worktrees | 3 | `git worktree list` |

**"No worse than baseline" = Cargo Deny and Coverage Gate were already red.**
Fixing them is upside; regressing the Go gate is forbidden.

## Root cause: dangling `phenotype-observably-macros`

- 11 `Cargo.toml` files reference `path = "../../../PhenoObservability/crates/phenotype-observably-macros"`.
- That path escapes the repo root. In CI (`/github/workspace`) it resolves to
  `/github/PhenoObservability/...` → `No such file or directory (os error 2)`.
- `PhenoObservability` is **absent from disk and absent from GitHub**
  (`gh repo view KooshaPari/PhenoObservability` → could not resolve).
- 42 call sites use `#[async_instrumented]`; the crate is genuinely needed.

**Consequence:** the only self-contained fix is an in-repo proc-macro crate.
Copying from upstream is impossible. This is a reconstruction, not a vendor.

## WBS + PERT

Estimates in minutes. `E = (O + 4M + P) / 6`.

| ID | Task | Depends on | O | M | P | E | Kill-safe output |
|---|---|---|---|---|---|---|---|
| 0.1 | Write this PLAN.md and commit | — | 10 | 15 | 25 | 15.8 | plan on disk |
| 0.2 | Record baseline table above | 0.1 | 5 | 8 | 12 | 8.2 | baseline committed |
| 1.1 | Author `crates/observability-macros` proc-macro (`async_instrumented`) | 0.2 | 20 | 35 | 60 | 36.7 | crate compiles alone |
| 1.2 | Repoint 11 `Cargo.toml` deps to `../observability-macros` | 1.1 | 10 | 15 | 30 | 16.7 | manifests consistent |
| 1.3 | `cargo metadata` + `cargo check` on the 11 crates | 1.2 | 8 | 15 | 30 | 16.3 | 11 crates still build |
| 1.4 | `cargo deny check` locally green | 1.3 | 5 | 10 | 20 | 10.8 | deny passes locally |
| 1.5 | Commit + push, watch CI | 1.4 | 5 | 8 | 15 | 8.7 | **CI checkpoint** |
| 2.1 | Classify 27 PRs (mergeable / conflicting / stale) | 0.2 | 5 | 8 | 10 | 7.8 | classification table |
| 2.2 | Close dependabot PRs targeting `_archived/` (#353,#354,#378,#387) | 2.1 | 8 | 12 | 20 | 12.7 | 4 PRs closed w/ reason |
| 2.3 | Merge mergeable non-conflicting PRs one at a time | 2.2 | 20 | 35 | 60 | 36.7 | one merge per commit |
| 2.4 | Disposition 11 conflicting PRs (rebase or close w/ reason) | 2.3 | 30 | 60 | 120 | 65.0 | each PR decided |
| 3.1 | `git branch -d` merged branches (safe delete only) | 2.4 | 2 | 3 | 5 | 3.2 | local branches pruned |
| 3.2 | `git worktree remove` the 2 extra worktrees | 3.1 | 3 | 5 | 10 | 5.5 | worktrees pruned |
| 3.3 | Disposition remaining local branches | 3.2 | 10 | 20 | 40 | 21.7 | each branch decided |
| 4.1 | Locate which IAC workspace is under 60% | 0.2 | 10 | 20 | 40 | 21.7 | named workspace |
| 4.2 | Fix or record explicit disposition for coverage gate | 4.1 | 20 | 45 | 90 | 48.3 | gate resolved or documented |
| 5.1 | `servers/external/mcpforge` — diagnose `TestDiagnostics/CleanFile` | 0.2 | 15 | 30 | 60 | 32.5 | cause named |
| 5.2 | `crates/hexa-kit/templates/go` — gate or exclude | 0.2 | 5 | 10 | 20 | 10.8 | disposition recorded |
| 5.3 | `crates/argis-extensions` — Go 1.26.7 + 152 gofmt violations | 0.2 | 20 | 45 | 90 | 48.3 | gate or exclude |

**Totals:** ΣE = 421.7 min. Longest chain `0 → E1 → E2 → E3` ≈ 242 min.
With E4/E5 delegated in parallel, wall-clock ≈ **4.0–4.5 h**.

## DAG

```mermaid
flowchart TD
    subgraph E0["E0 · Closure anchor (first, tiny)"]
        A1["0.1 Write + commit PLAN.md<br/>15.8m"]:::cp
        A2["0.2 Record verified baseline<br/>8.2m"]:::cp
        A1 --> A2
    end

    subgraph E1["E1 · Unblock Cargo Deny — dangling dep"]
        B1["1.1 Author observability-macros<br/>36.7m"]
        B2["1.2 Repoint 11 Cargo.toml<br/>16.7m"]
        B3["1.3 cargo metadata + check x11<br/>16.3m"]
        B4["1.4 cargo deny check<br/>10.8m"]
        B5["1.5 Commit + push → CI<br/>8.7m"]:::cp
        B1 --> B2 --> B3 --> B4 --> B5
    end

    subgraph E2["E2 · PR backlog burn-down (27)"]
        C1["2.1 Classify PRs<br/>7.8m"]
        C2["2.2 Close archived-path dependabot x4<br/>12.7m"]:::cp
        C3["2.3 Merge mergeable PRs<br/>36.7m"]:::cp
        C4["2.4 Disposition 11 conflicting<br/>65.0m"]:::cp
        C1 --> C2 --> C3 --> C4
    end

    subgraph E3["E3 · Branch + worktree hygiene"]
        D1["3.1 git branch -d merged<br/>3.2m"]
        D2["3.2 Prune worktrees<br/>5.5m"]
        D3["3.3 Disposition 24 branches<br/>21.7m"]:::cp
        D1 --> D2 --> D3
    end

    subgraph E4["E4 · Coverage Gate (pre-existing red)"]
        F1["4.1 Name the sub-60% IAC workspace<br/>21.7m"]
        F2["4.2 Fix or record disposition<br/>48.3m"]:::cp
        F1 --> F2
    end

    subgraph E5["E5 · Residual Go modules (lowest value)"]
        G1["5.1 mcpforge lsp test<br/>32.5m"]
        G2["5.2 hexa-kit template<br/>10.8m"]
        G3["5.3 argis-extensions<br/>48.3m"]
    end

    A2 --> B1
    A2 --> C1
    A2 --> F1
    A2 --> G1
    A2 --> G2
    A2 --> G3
    C4 --> D1
    B5 --> C1
    B5 --> D1

    classDef cp fill:#1b5e20,stroke:#4caf50,stroke-width:2px,color:#fff
```

Green nodes are **kill-safe checkpoints**: state is committed and the repo is
no-worse-than-baseline at that point.

## Schedule (PERT view)

```mermaid
gantt
    title PhenoShared closure — critical path
    dateFormat HH:mm
    axisFormat %H:%M

    section E0 anchor
    0.1 PLAN.md + commit        :a1, 00:00, 16m
    0.2 Baseline                :a2, after a1, 8m

    section E1 Cargo Deny
    1.1 observability-macros    :b1, after a2, 37m
    1.2 Repoint 11 manifests    :b2, after b1, 17m
    1.3 metadata + check        :b3, after b2, 16m
    1.4 cargo deny              :b4, after b3, 11m
    1.5 Push + CI               :b5, after b4, 9m

    section E2 PR backlog
    2.1 Classify                :c1, after b5, 8m
    2.2 Close archived x4       :c2, after c1, 13m
    2.3 Merge mergeable         :c3, after c2, 37m
    2.4 Conflicting x11         :c4, after c3, 65m

    section E3 Hygiene
    3.1 branch -d               :d1, after c4, 3m
    3.2 worktree remove         :d2, after d1, 6m
    3.3 Branch disposition      :d3, after d2, 22m

    section E4 Coverage
    4.1 Name workspace          :f1, after a2, 22m
    4.2 Fix or disposition      :f2, after f1, 48m

    section E5 Go residual
    5.1 mcpforge                :g1, after a2, 33m
    5.2 hexa-kit                :g2, after a2, 11m
    5.3 argis-extensions        :g3, after a2, 48m
```

## Kill recovery

| Killed during | Repo state | Recovery |
|---|---|---|
| 0.1 / 0.2 | clean | Re-run from this file. |
| 1.1 | new crate dir, uncommitted | `git status`; crate is additive, safe to commit or discard. Manifests untouched, so build is unaffected. |
| 1.2 | some manifests repointed | **Dangerous window.** Partially-repointed manifests may not resolve. Recovery: `git checkout -- crates/*/Cargo.toml`, then redo 1.1–1.2 as one unit. |
| 1.3 / 1.4 | committed or clean | Re-run the failing command. |
| 1.5 | pushed, CI running | Read CI result from GH; no local work lost. |
| 2.x | clean per-PR | `gh pr list` tells you exactly what remains. |
| 3.x | clean | Branch list is the state. |
| 4.x / 5.x | clean | Documented disposition table is the state. |

**The single unsafe window is 1.2.** Mitigation: apply all 11 manifest edits and
verify in one uninterrupted step, or not at all.

## Status

- [ ] E0 anchor
- [ ] E1 Cargo Deny unblocked
- [ ] E2 PR backlog → 0
- [ ] E3 branches/worktrees pruned
- [ ] E4 coverage gate resolved or dispositioned
- [ ] E5 residual Go modules dispositioned/SKIPPED
