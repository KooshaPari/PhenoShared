# PlusForges Member Fork Index Docket

**Date:** 2026-07-29
**Auditor:** Forge-Code (autonomous consolidation pass)

---

## STATUS: ❌ SPONSOR DENY 2026-07-29 — G7 NO SQUASH

**Sponsor decision (2026-07-29 transcript):**
> *"g3a g4 ok g5 no only squash lattr as you consume into foremr g4 no g7 no NEVER squas parent repos with deep improtnat histories. only a cosnumed REPO AND ONLY AS A NEW MAIN BRANCH WHILE YOU KEEP ONE FULL HISTOIRY OR OTHER FULL HIST RBANCEHS PRESENT"*

**Decoded:**
- **G7: DENY** — `agentapi-plusplus`, `cliproxyapi-plusplus`, `context-mode-plusplus`, and `PlusForges` are **parent repos** (forks of distinct upstreams). They are **never squashed** under the new policy.
- Each fork retains its full history independently. No branch deletion, no remote deletion, no force-push.

### What This Means for the PlusForges members

| Repo | Banches | Status |
|---|---|---|
| `agentapi-plusplus` | 1 | parent (fork of `coder/agentapi`) → frozen |
| `cliproxyapi-plusplus` | 4 | parent (fork of `router-for-me/CLIProxyAPI`) → frozen |
| `context-mode-plusplus` | 1 | parent (upstream-fork) → frozen |
| `PlusForges` | 1 | meta-pointer → frozen |

| Operation | Status |
|---|---|
| Branch manifest export (Lane-3) | ✅ permitted without ACK |
| SHA-256 checksums (Lane-3) | ✅ permitted without ACK |
| Upstream-sync verification (read-only) | ✅ permitted without ACK |
| Repo squash to 1 commit | ❌ **permanently forbidden** (parent repo) |
| Branch deletion | ❌ **permanently forbidden** |
| Force-push to `main` | ❌ **permanently forbidden** |

These forks are **frozen as-is**. Future work proceeds on feature branches; `main` and all other branches are immutable. Upstream sync work, if any, happens on new feature branches.

---

**Status:** MIGRATION PROPOSED — DENIED; repos frozen as parent-per-policy

---

## Members in Scope

| Repo | Default | Branches | Last Push | Local Clone | Upstream |
|---|---|---|---|---|---|
| `agentapi-plusplus` | main | 1 | 2026-07-29 | ❌ | `coder/agentapi` |
| `cliproxyapi-plusplus` | main | 4 | 2026-07-29 | ✅ `/repos/cliproxyapi-plusplus` | `router-for-me/CLIProxyAPI` |
| `context-mode-plusplus` | main | 1 | 2026-07-29 | ❌ | (upstream-fork) |
| `PlusForges` | main | 1 | 2026-06-25 | ❌ | (meta-repo) |

## MIGRATE — semantic content mapping

These are **independent forks of distinct upstreams** — they are NOT duplicates of each other. `PlusForges` is the meta-index repo that lists them; the actual forks live in their own repos.

| Source | Target | Rule | Notes |
|---|---|---|---|
| `PlusForges` | pointer | meta | README-only list linking out to all `*+-plusplus` forks |
| `agentapi-plusplus` | canonical | n/a | Fork of `coder/agentapi` |
| `cliproxyapi-plusplus` | canonical | n/a | Fork of `router-for-me/CLIProxyAPI`; local clone has origin+upstream remotes |
| `context-mode-plusplus` | canonical | n/a | Upstream-fork; standalone |

## STATE — current branches

```
agentapi-plusplus:           main (single branch)
cliproxyapi-plusplus:        main + 3 develop branches
context-mode-plusplus:       main (single branch)
PlusForges:                  main (README-only)
```

## ABSORBED — confirmed content states

- **`agentapi-plusplus`** → independent fork; no absorption expected.
- **`cliproxyapi-plusplus`** → independent fork; no absorption expected.
- **`context-mode-plusplus`** → independent fork; no absorption expected.
- **`PlusForges`** → meta-pointer; no novel content.

## SUPERSEDES — receipts preserved

Each fork retains its own history. No archive repos in this family.

## PROPOSED MUTATIONS (NOT EXECUTED — pending approval)

1. `agentapi-plusplus` → squash to 1 commit on `main`.
2. `cliproxyapi-plusplus` → squash to 1 commit on `main`.
3. `context-mode-plusplus` → squash to 1 commit on `main`.
4. `PlusForges` → leave as meta-pointer README (no squash needed; 1 branch total).

**Upstream sync verification (recommended before squash):**

```
git remote add upstream https://github.com/coder/agentapi.git
git remote add upstream https://github.com/router-for-me/CLIProxyAPI.git
git fetch upstream --quiet
git rev-list --count upstream/main ^main    # unique upstream commits
git rev-list --count main ^upstream/main    # unique local commits
```

For each fork, this verifies whether local is ahead/behind upstream. The user's stance is "Plus" forks carry <REDACTED> patches on top of upstream.

## LOCAL CHECKOUT COVERAGE

- `/repos/cliproxyapi-plusplus` (origin/upstream): 4/4 branches local ✅
- Other 3 forks: single-branch only; no local clone needed.

## RISK CLASS

**Low.** Small forks; no cross-fork conflicts.

## NEXT CHECKPOINT

User must approve:
- (a) upstream-sync verification per fork
- (b) squash of each fork to 1 commit on `main` (separately or together)
