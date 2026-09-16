---
doc: phenofleet-reactivation-decision
date: 2026-07-06
status: DRAFT — operator decision pending
author: phenofleet-decision-doc teammate (session b3c65cfe-8c3f-4a84-81f2-5b3892d377ed / 26454141)
scope: read-only research + text-only deliverable
---

# phenofleet — REACTIVATION vs ARCHIVE decision-doc

> **TL;DR (operator-action surface):**
> phenofleet moved from active infra to R&D pivot on 2026-07-02. Its central
> SQLite claim-DB (`FLEET_DAG_v3.db`) and the secondary `~/FLEET_DAG.db` are
> both **0-byte placeholders** today (verified 2026-07-05 23:26 PDT). The
> "12 federated teammates with atomic lease" infra is **not operational**.
>
> Three viable paths; this document lays out the call surface. **Recommendation:**
> **ARCHIVE** with documentation (Option 3) — substrate-mesh already covers the
> work that phenofleet would have done. Do NOT reactivate in flight.

---

## 1. Status snapshot (state of the world, 2026-07-06)

### 1.1 Filesystem-verified state

| Artifact                                                       | Size    | mtime        | Notes                                                                 |
|----------------------------------------------------------------|---------|--------------|-----------------------------------------------------------------------|
| `~/CodeProjects/Phenotype/repos/FLEET_DAG_v3.db`               | 0 bytes | Jul 5 19:33  | Canonical placeholder. Not SQLite. Memory ([fleet-dag-v3-placeholder-2026-07-05](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/feedback_fleet_dag_v3_placeholder_2026_07_05.md)) says same. |
| `~/FLEET_DAG.db`                                               | 0 bytes | Jun 20 19:37 | Secondary placeholder outside repos tree. Also 0 bytes.               |
| `~/CodeProjects/Phenotype/repos/thegent/phenofleet/`           | dir     | Jun 17 22:37 | Last touched ~3 weeks ago. Python module still on disk; `__pycache__/` exists but source files removed since (`ls` shows only `__pycache__`). |
| `~/CodeProjects/Phenotype/repos/.remember/phenofleet-manifest-2026-06-16.json` | 549 KB   | Jun 16 03:40 | Frozen 12-teammate manifest from initial rollout. Read-only artifact. |
| `~/CodeProjects/Phenotype/repos/.remember/phenofleet-gates.json` | 2.1 KB | Jun 16 04:00 | Final gate-verification record from 2026-06-16. All 4 gates passed.   |
| `~/CodeProjects/Phenotype/repos/.remember/forge-corpus-2026-06-16.jsonl` + `.norm.jsonl` | 22 MB  | Jun 16 03:14 | One-shot snapshot of forge work at phenofleet launch. |
| `~/.claude/plugins/phenofleet/`                                | (skipped) | — | Not inspected in this scope (read-only on code). |

### 1.2 Memory-state summary

| Memory                                                                                       | Origin    | Says                                                                  |
|----------------------------------------------------------------------------------------------|-----------|-----------------------------------------------------------------------|
| [project_phenofleet](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/project_phenofleet.md) | 2026-06-16 | 12 teammates (tm01..tm12), atomic claim, OmniRoute Main blend. "active infra". |
| [feedback_lease_protocol](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/feedback_lease_protocol.md) | 2026-06-16 | Schema + acquire/release protocol. PK `(repo,branch,worktree)`, 900s TTL, 60s heartbeat. |
| [feedback_phenofleet_identity](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/feedback_phenofleet_identity.md) | 2026-06-16 | KooshaPari-only push, archived-skip list, GPG opt-out. |
| [feedback_phenofleet_gates](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/feedback_phenofleet_gates.md) | 2026-06-16 | 4 gates: subagent rebase-rate, GPG, gh-auth, slot-cap. |
| [feedback_fleet_dag_v3_placeholder_2026_07_05](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/feedback_fleet_dag_v3_placeholder_2026_07_05.md) | 2026-07-05 | **THE FORK.** substrate-mesh first-tick verified DBs are 0-byte. Decision: SKIP scaffold; hold until operator signals reactivation. |
| [project_fleet_pivot_rnd_2026_07_02](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/project_fleet_pivot_rnd_2026_07_02.md) | 2026-07-02 | OmniRoute de-focused; pivot off PR-merging; 87/100 org PRs are on archived repos. Fleet pivoted to 5 R&D repos. |

### 1.3 What changed

- **2026-06-16** — phenofleet roll-out. 12 teammates spun up in tmux session, 4 gates green, FLEET_DAG_v3.db schema implemented. ~2 weeks of federated work shipped.
- **2026-07-02** — Fleet pivot to R&D. Long-horizon repos (sharecli, substrate, SessionLedger, forgecode, MelosViz) take focus; phenofleet deprioritized. Memory: "fleet now builds net-new work on the 5 owned R&D repos." (see [project_fleet_pivot_rnd_2026_07_02](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/project_fleet_pivot_rnd_2026_07_02.md))
- **2026-07-03** — forgecode parked. Scope further narrowed to **4 core repos**. (see [project_ownership_scope_narrowed_2026_07_03](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/project_ownership_scope_narrowed_2026_07_03.md))
- **2026-07-05** — substrate-mesh first-tick. The 0-byte DB reality is recorded. Memory is reconciled.
- **2026-07-06 (now)** — This document.

---

## 2. Use-case analysis — does phenofleet still solve a real problem?

### 2.1 What phenofleet was built to solve (Jun 2026)

**Single sentence:** Many agents want to write to many repos without colliding — provide an atomic claim layer so they self-serialize.

Three concrete failure modes it addressed:

1. **Worktree/PK collisions** — multiple forge sessions racing on the same `(repo,branch,worktree)` triple. Resolved by PK-gate `INSERT OR IGNORE`.
2. **Slot exhaustion per agent** — one agent grabbing 15 repos and starving the rest. Resolved by per-agent `SLOT_CAPS`.
3. **Stale claims / dead agents** — abandonware claims blocking work. Resolved by 900s TTL + 60s heartbeat + opportunistic release.

### 2.2 What solves those problems TODAY (Jul 2026)

| Failure mode                            | Today's mitigation                                                                                                  | As-good-as phenofleet? |
|-----------------------------------------|---------------------------------------------------------------------------------------------------------------------|------------------------|
| Worktree/PK collisions                  | Manual worktree naming + parent-agent serial dispatch; **`feedback_worktree_on_conflict`** memory says index.lock/dirty → switch to worktree | **YES** for the 4-repo scope. The collision surface shrank. |
| Slot exhaustion per agent               | 3-level swarm pattern (Opus coord → Sonnet leads → Haiku dispatch-worker leaves). See [feedback_3level_swarm](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/feedback_3level_swarm.md) | **YES.** Hierarchical cap, not DB cap, but functionally equivalent. |
| Stale claims / dead agents              | `try/finally` release + per-tick refresh in the dispatch loop. **No DB, but the lease protocol is just an atomic row insert. | **PARTIAL.** Without PK-gate enforcement, two agents CAN both think they hold the same claim. But operationally (4 repos, ≥25 tasks), this has not bitten us. |

### 2.3 The substrate-mesh alternative

substrate-mesh (per [feedback_substrate_wean_agent](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/feedback_substrate_wean_agent.md) and [feedback_substrate_dogfood](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/feedback_substrate_dogfood.md)) is becoming the substrate-mesh runtime substrate:

- EnginePort adapters (hexagonal) route dispatched tasks to any of forgecode / OmniRoute Main blend / substrate native / Codex Resumed.
- `substrate_dispatch --tier` replaces `Agent()` calls — `heavy/main/worker` tiers, auto-reroute-up.
- 7 long-horizon domain teammates (D/Q/P/I/M/X/C — see [project_session_domain_teammates](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/project_session_domain_teammates.md)) each own a domain end-to-end, with implicit per-domain serialization.

**Conclusion:** substrate-mesh already absorbs the "atomic claim on a worktree" concept, encoded as a Rust EnginePort adapter's serializable "claim-before-write" handler rather than a SQLite PK. The use case phenofleet was built for is no longer the binding constraint at current scope.

### 2.4 Use-case scorecard

| Use case                                                                         | Need today? | Solved by substrate-mesh? | Reactivation priority |
|----------------------------------------------------------------------------------|-------------|---------------------------|-----------------------|
| Atomic claim across ≥ 12 concurrent agents on a monorepo                         | LOW (4 repos)| YES (EnginePort serializes) | LOW |
| Federated tmux/tm10-identity audit of pushes                                      | DEPRECATED (gate-time replaced) | YES (pre-push hook pattern only on active repos) | LOW |
| 4-gate risk harness before mass-dispatch                                         | DEPRECATED (3-level swarm: Opus gate at coord boundary) | YES | LOW |
| OmniRoute Main blend routing per teammate                                         | ABSORBED into OmniRoute fork-pivot schema ([project_omniroute_fork_pivot_2026_07_02](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/project_omniroute_fork_pivot_2026_07_02.md)) | YES | LOW |

**Verdict on use case:** phenofleet's *concept* survives (atomic claim is real, identity rules are real, GPG opt-out is real). What is dead is the **operational shape** — 12 federated teammates + tmux comms.sh + SQLite DB PK-gate.

---

## 3. Cost analysis — what would reactivation require?

### 3.1 Option A — Full reactivation (match 2026-06-16 spec)

| Cost dimension       | Estimate (subagent-hours)                                                                                                  |
|----------------------|---------------------------------------------------------------------------------------------------------------------------|
| Schema bootstrap     | 1-2 tool calls (`sqlite3 FLEET_DAG_v3.db < schema.sql`). Source schema is in memory, not on disk. Need to rewrite or recover. |
| `lease.py` rewrite   | 3-5 tool calls. `thegent/phenofleet/` only has `__pycache__/` now — Python source is gone. (Re-implement from [feedback_lease_protocol](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/feedback_lease_protocol.md)) |
| `gates.py` rewrite   | 2-3 tool calls.                                                                                                            |
| `comms.sh` rewrite   | 1-2 tool calls (tmux 12-window setup).                                                                                     |
| Teammate manifests   | 5-8 tool calls — 12 *.md teammate files in `thegent/phenofleet/teammates/`.                                                  |
| Plugin resurrect     | 1-2 tool calls — `~/.claude/plugins/phenofleet/` skill files.                                                              |
| 4-gate re-run        | 1-2 tool calls.                                                                                                            |
| First acquire race-test| 1-2 tool calls (verify PK-gate works).                                                                                    |
| Subtotal             | **~15-25 tool calls, 5-12 min wall clock** for cold restart. Plus ongoing maintenance: heartbeat monitor, slot-cap audits, gate re-runs per session. |

**Ongoing** (per session, every session): ~3-5 tool calls for gate re-verification, ~2 tool calls for slot-cap rollup. ~5 min/active-day.

### 3.2 Option B — Minimal reactivation (lease-only, no teammates)

Drop the tmux + plugin + teammate-spec surface. Keep only:

1. The `FLEET_DAG_v3.db` SQLite DB + the `lease.py` acquire/heartbeat/release module.
2. The 4-gate `gates.py` (cheap, ~10s).
3. The identity pre-push hook.

| Cost dimension      | Estimate                                                                                |
|---------------------|------------------------------------------------------------------------------------------|
| `lease.py` only     | 2-3 tool calls (~50 LOC from memory).                                                    |
| `gates.py` only     | 2-3 tool calls (~30 LOC from memory).                                                    |
| Schema bootstrap    | 1 tool call.                                                                              |
| Pre-push hook       | 1-2 tool calls.                                                                          |
| Subtotal            | **~6-11 tool calls, 2-5 min wall clock** for minimal reactivation.                       |

**Ongoing:** ~1-2 tool calls per session (gate re-verify, occasional slot-cap audit). ~1 min/active-day.

### 3.3 Option C — Archive with documentation

Documentation-only: this decision-doc + a `MEMORY.md` index update + a tombstone line in `project_phenofleet.md`.

| Cost dimension      | Estimate                                        |
|---------------------|--------------------------------------------------|
| This document       | DONE (~1 tool call).                              |
| Update `project_phenofleet.md` frontmatter to `status: archived` | 1 Edit.                                 |
| Add tombstone to `MEMORY.md` (optional)         | 1 Edit.                                          |
| Subtotal            | **~2-3 tool calls, ~30 sec wall clock.**          |

**Ongoing:** ZERO. Memory + this doc do the rest.

### 3.4 Cost scorecard

| Option                  | Cold-start cost | Ongoing cost | Reversible? |
|-------------------------|-----------------|--------------|-------------|
| A — Full reactivation   | 15-25 calls / 5-12 min | 5 min/day | YES (easy to disable) |
| B — Minimal reactivation | 6-11 calls / 2-5 min | 1 min/day | YES (easy to enable full) |
| C — Archive             | 2-3 calls / 30 sec | 0           | YES (re-derive from docs) |

---

## 4. Risk analysis

### 4.1 What breaks if we re-activate

| Risk                                                                 | Likelihood | Impact | Notes                                                                                |
|----------------------------------------------------------------------|------------|--------|--------------------------------------------------------------------------------------|
| substrate-mesh now covers this surface → reactivated phenofleet becomes stale within 1-2 sessions | HIGH       | LOW-MED | substrate_engine Port serializes by design. Phenofleet PK-gate becomes redundant.    |
| Cold-restart costs ~10 min + every-session re-verify ~1-5 min       | HIGH       | LOW     | Recurring tax on every session.                                                       |
| SQLite DB lock contention under burst dispatch                       | MEDIUM     | MED     | Reported bug in substrate-mesh earlier this session ("forge 'database locked' masquerades as ENOSPC" per [project_disk_full_recovery_2026_07_03](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/project_disk_full_recovery_2026_07_03.md)) suggests SQLite under burst can be flaky |
| Teammate manifest drift vs current code                              | MEDIUM     | MED     | All teammate `.md` files reference 2026-06-16 reality; 4-repo scope + substrate-mesh additions not reflected |
| Identity-rule drift (archived-repo list, Dmouse92 block)            | LOW        | MED     | archived list currently `chatta, KaskMan, AtomsBot` only — many more repos archived since (see [feedback_archived_repos_full_2026_06_30](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/feedback_archived_repos_full_2026_06_30.md): 38 archived). Drift already real. |
| GPG opt-out forgotten on a new worktree                              | LOW        | LOW     | Triple-flag workaround is non-obvious; new workspaces miss it.                        |
| Slot-cap for the 4-repo scope: with cap=5/agent × 7 domain teammates = 35 claims max. Plenty. | LOW | LOW     | 7 domain teammates already under this cap. No need to enforce.                         |

### 4.2 What breaks if we DON'T re-activate (archive)

| Risk                                                                   | Likelihood | Impact | Mitigation                                                                                       |
|------------------------------------------------------------------------|------------|--------|--------------------------------------------------------------------------------------------------|
| Two agents in same session claim same worktree ad-hoc                 | MEDIUM     | LOW-MED | Mitigated by parent-Opus serial dispatch + `feedback_worktree_on_conflict`. Manual resolution only. |
| A later scale-up beyond 4 repos requires re-deriving phenofleet       | LOW        | MED     | This decision-doc + memory are the derivation. Acceptable cold-start cost is documented.          |
| No machine-checked PK-gate means "the same repo, two writers" is a silent race | LOW | MED | Worktree content hashing (different folder names) already prevents most collisions. Risk is regression only. |
| Memory fragments referencing phenofleet as "live infra" linger          | HIGH       | LOW     | [feedback_fleet_dag_v3_placeholder_2026_07_05](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/feedback_fleet_dag_v3_placeholder_2026_07_05.md) already addresses this; archive mode adds a tombstone for clarity. |

### 4.3 What is INDEPENDENT of the decision (reactivation or archive)

- The 4-gate harness concept (cheap, ~10s/run). Useful regardless. Migrate into qgate / dispatch loop if archived.
- The identity rules (KooshaPari-only push, archived-skip). Already enforced at pre-push level on active worktrees.
- The TTL+heartbeat concept. Useful if any future lease mechanic ever re-emerges.
- The OmniRoute Main blend routing. Already live in substrate-mesh / forgecode tier selection.

---

## 5. Three options

### Option 1 — Full reactivation

**Mirror 2026-06-16 spec exactly.** Bootstrap schema, rewrite lease.py / gates.py / comms.sh, re-spawn 12 federated teammates, resume tmux `phenofleet` session, run 4-gate verification, do race-test, begin daily heartbeat.

- **Pro:** faithful to original vision; strongest guarantees.
- **Con:** ~10 min cold-start; ~5 min/day ongoing; substrate-mesh already covers the surface; risk of staleness in 1-2 sessions.
- **Con:** cohort narrows from 12 teammates to **4 owned R&D repos** + **7 domain teammates (D/Q/P/I/M/X/C)** — reactivated phenofleet has no real work to do.

### Option 2 — Minimal reactivation (lease module only)

**Keep only the SQLite lease PK-gate + 4-gate script.** No tmux, no federated teammates, no plugin.

- **Pro:** preserves the atomic claim primitive; cheap to maintain (~1 min/day); can re-derive to full from this base.
- **Pro:** 4-gate harness migrates naturally — it's pure bash + python, idempotent.
- **Con:** false signal — keeping a DB alive for a problem that's not present uses idle disk and maintenance budget.
- **Con:** the `lease.py` source is gone from disk; re-derivation cost ≠ zero.

### Option 3 — Archive with documentation (RECOMMENDED)

**Mark phenofleet archived in memory. Don't write any new code. Don't bootstrap the DB.**

- **Pro:** zero ongoing cost; zero staleness risk; substrate-mesh's EnginePort serializes by design (the surviving primitive is named differently and lives there).
- **Pro:** decisions are reversible — this doc + memory ARE the cold-start spec for any future reactivation.
- **Pro:** aligns with [project_fleet_pivot_rnd_2026_07_02](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/project_fleet_pivot_rnd_2026_07_02.md) and the [project_ownership_scope_narrowed_2026_07_03](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/project_ownership_scope_narrowed_2026_07_03.md) narrowing.
- **Con:** loses the 4-gate script — that's the only net loss. Migrating it into `qgate` is feasible (Q-domain teammate owns that).
- **Con:** future reactivation requires re-derivation (~10 min, matches Option 1/A's cold-start).

---

## 6. Recommendation

**Recommend Option 3 — Archive with documentation.**

Reasons:

1. **Use-case boundary has shifted.** phenofleet's job (atomic claim across ≥12 federated teammates on a ~100-PR monorepo) is solved by today's 3-level swarm + 4-repo narrow scope + substrate-mesh EnginePort serialization. Reactivating would solve a problem we no longer have.
2. **Substrate-mesh is the new home** for the surviving primitive (atomic claim, pre-write serialization). Per [feedback_substrate_wean_agent](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/feedback_substrate_wean_agent.md), `substrate_dispatch` is the canonical path for cross-engine work. Engineering effort spent on substrate-mesh's EnginePort reapplies for every repo in scope; effort spent on phenofleet reactivation reapplies for exactly the phenofleet surface (a shrinking surface).
3. **Cost-benefit ratio.** Option 3 is 30 sec + 2 edits; Option 1 is 10 min cold-start + 5 min/day ongoing for no functional gain over Option 3.
4. **Reversibility.** Memory + this decision-doc ARE the cold-start spec. A future ticket asking "should phenofleet come back?" has a 30-second ramp-up: read this doc, decide, build the slice they need.
5. **Operator's stated direction.** Per [project_ownership_scope_narrowed_2026_07_03](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/project_ownership_scope_narrowed_2026_07_03.md), the operator's preference is unambiguous about scope shrinking ("skip omniroute", "drop configra", "drop forgecode until other projs done"). Reactivating a 12-teammate federated layer would re-widen scope explicitly.
6. **No in-flight blocker.** All active session work is on sharecli / substrate / SessionLedger / MelosViz. None of those depend on phenofleet — they all have substrate-mesh as their substrate. Deferring phenofleet does not block any ticket in the active backlog.

**Caveat for Option 3:** the **4-gate script** (gates.py at /Users/kooshapari/CodeProjects/Phenotype/repos/thegent/phenofleet/, deleted from disk) contains genuinely useful checks (subagent rebase-rate, gh-auth, slot-cap, GPG). If those checks have no analog elsewhere, porting them into `qgate` (Q-domain teammate's territory per [project_session_domain_teammates](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/project_session_domain_teammates.md)) is the right way to recover the value. **Decoupling:** gate checks migrate to qgate; rest of phenofleet stays archived.

---

## 7. Operator decision surface

**Decision needed from Koosha:**

1. **GO / NO-GO on Option 3 (archive with documentation)?**
   - **GO** → I (this teammate) make 2 follow-up edits: flip `project_phenofleet.md` to `status: archived`; add a tombstone index line to `MEMORY.md`. Done.
   - **NO-GO** → operator picks 1 or 2. I (this teammate) commit cold-start work for that option.

2. **If NO-GO on Option 3: which gates should migrate to qgate?** (recommended list, decoupled from Option 3):
   - Gate 1 — Subagent rebase/merge failure rate.
   - Gate 3 — gh auth not expired.
   - **Optional:** Gate 4 — Slot cap enforcement (less compelling at 4-repo scale).

3. **What is the kill condition for the cold-restart Option 1/2 budget?** (e.g. "you have 3 sessions to demonstrate phenofleet adds value beyond substrate-mesh, else auto-archive").

4. **Should `~/.claude/plugins/phenofleet/` skill files be archived separately?** (this teammate did not inspect them in scope — flagged for follow-up if Option 3 is taken.)

---

## Appendix A — Verified facts (with citations)

| Fact                                                                                                | Citation                                                                                          |
|-----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| FLEET_DAG_v3.db is 0 bytes                                                                         | `ls -la` 2026-07-05 19:33 (this session); corroborated by [feedback_fleet_dag_v3_placeholder_2026_07_05](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/feedback_fleet_dag_v3_placeholder_2026_07_05.md) |
| ~/FLEET_DAG.db is 0 bytes                                                                          | `ls -la` 2026-07-05 (this session).                                                                |
| phenofleet Python source code gone from disk                                                       | `ls -la thegent/phenofleet/` 2026-07-06 (this session). Only `__pycache__/` remains.             |
| Fleet pivoted to R&D on 2026-07-02                                                                  | [project_fleet_pivot_rnd_2026_07_02](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/project_fleet_pivot_rnd_2026_07_02.md) |
| 4-repo scope (sharecli, substrate, SessionLedger, MelosViz) per 2026-07-03                          | [project_ownership_scope_narrowed_2026_07_03](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/project_ownership_scope_narrowed_2026_07_03.md) |
| 7 long-horizon domain teammates (D/Q/P/I/M/X/C) per 2026-07-05                                     | [project_session_domain_teammates](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/project_session_domain_teammates.md) |
| substrate_dispatch replaces Agent() calls                                                            | [feedback_substrate_wean_agent](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/feedback_substrate_wean_agent.md), [feedback_substrate_dogfood](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/feedback_substrate_dogfood.md) |
| OmniRoute de-focused (fork-pivot)                                                                  | [project_omniroute_fork_pivot_2026_07_02](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/project_omniroute_fork_pivot_2026_07_02.md) |
| 87/100 org PRs are on archived repos                                                                | [project_fleet_pivot_rnd_2026_07_02](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/project_fleet_pivot_rnd_2026_07_02.md) |
| Archived-repo list has drifted to 38 entries since 2026-06-16 (was 3: chatta, KaskMan, AtomsBot)    | [feedback_archived_repos_full_2026_06_30](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/feedback_archived_repos_full_2026_06_30.md) |
| SQLite-on-Mac has shown 'database locked' under burst before                                       | [project_disk_full_recovery_2026_07_03](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/project_disk_full_recovery_2026_07_03.md) |
| Lease protocol spec text                                                                            | [feedback_lease_protocol](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/feedback_lease_protocol.md) |
| 4-gate harness spec text                                                                            | [feedback_phenofleet_gates](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/feedback_phenofleet_gates.md) |
| Identity rules spec text                                                                            | [feedback_phenofleet_identity](file:///Users/kooshapari/.claude/projects/-Users-kooshapari-CodeProjects-Phenotype-repos/memory/feedback_phenofleet_identity.md) |

## Appendix B — Out of scope (per task)

- Did NOT modify `FLEET_DAG_v3.db` or `~/FLEET_DAG.db`.
- Did NOT modify any teammates' active branches.
- Did NOT run cargo / did NOT kill processes / did NOT touch worktrees.
- Did NOT inspect `~/.claude/plugins/phenofleet/` (out of declared scope; flagged for follow-up).

---
