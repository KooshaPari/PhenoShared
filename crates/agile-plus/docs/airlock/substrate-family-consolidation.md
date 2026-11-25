# Substrate Family Consolidation Docket

**Date:** 2026-07-29
**Auditor:** Forge-Code (autonomous consolidation pass)

---

## STATUS: ❌ SPONSOR DENY 2026-07-29 — G5 NO SQUASH

**Sponsor decision (2026-07-29 transcript):**
> *"g3a g4 ok g5 no only squash lattr as you consume into foremr g4 no g7 no NEVER squas parent repos with deep improtnat histories. only a cosnumed REPO AND ONLY AS A NEW MAIN BRANCH WHILE YOU KEEP ONE FULL HISTOIRY OR OTHER FULL HIST RBANCEHS PRESENT"*

**Decoded:**
- **G5: DENY** — `substrate` and `substrate-adapters-bundle` are **parent repos** with deep history (100 and 7 branches respectively). They are **never squashed** under the new policy.
- Only **consumed** repos may be squashed (and only as a NEW branch, with full history retained).
- Lane-3 read-only deepening (branch manifests export, SHA-256 checksums) remains available without ACK.

### What This Means for `substrate` (100 branches) and `substrate-adapters-bundle` (7 branches)

| Operation | Status |
|---|---|
| Branch manifest export (Lane-3) | ✅ permitted without ACK |
| SHA-256 checksums (Lane-3) | ✅ permitted without ACK |
| Repo squash to 1 commit | ❌ **permanently forbidden** (parent repo) |
| Branch deletion | ❌ **permanently forbidden** |
| Remote deletion | ❌ **permanently forbidden** |
| Force-push to `main` | ❌ **permanently forbidden** |

These repos are **frozen as-is**. Future work proceeds on feature branches; `main` and all other branches are immutable.

---

**Status:** MIGRATION PROPOSED — DENIED; repo frozen as parent-per-policy

---

## Members in Scope

| Repo | Default | Branches | Last Push | Local Clone |
|---|---|---|---|---|
| `substrate` | main | **100** | 2026-07-29 | ❌ |
| `substrate-adapters-bundle` | main | 7 | 2026-07-29 | ❌ |

## MIGRATE — semantic content mapping

| Source | Target | Rule | Notes |
|---|---|---|---|
| `substrate` | canonical | n/a | 100 branches; public; canonical substrate ecosystem repo |
| `substrate-adapters-bundle` | canonical | n/a | 7 branches; meta-repo of substrate adapter crates (git-submodule pointers); review/ownership branches indicate recent governance work |

**Cross-branch collision scan result: ZERO common branch names.**
`substrate` and `substrate-adapters-bundle` are **independent repos** — neither duplicates the other.

### Substrate (100 branches) — branch taxonomy

```
airlock-archive/wave4/wt-stale/substrate-58a1d88-2026-07-16.tar
airlock-archive/wave4/wt-stale/substrate-76bbb44-2026-07-16.tar
archive/thegent-dispatch/chore-sha-pin-2026-06-16
archive/thegent-dispatch/feat-agents-adr-crossref-2026-06-20
archive/thegent-dispatch/main
bench/f5-forge-daemon-m8-m16-m32
chore/agent-readiness-hardening
chore/agent-readiness-p4-v2
chore/ci
chore/clippy-polish
chore/dx-justfile
chore/fix-cloud-publish-flake
chore/l116-cockpit-polish
chore/l117-cycle-stamp
chore/rebase-substrate-193-onto-main
chore/rebase-substrate-211-onto-main
chore/release-scorecard-proof
chore/release-v0.3.{3..10}
chore/scorecard-nextest-certification
ci/dx-sccache
ci/registry-publish
ci/security-workflow-syntax
cursor/identified-system-bugs-44a2
cursor/integration-and-tracing-issues-1d3d
dependabot/cargo/{...,futures-0.3.33,serde_json-1.0.151,tokio-1.53.0,uuid-1.24.0}
dependabot/github_actions/github-actions-02325a8da5
docs/{dispatch-migration-2026-06-30,dx-devcontainer-evidence,dx-rust-analyzer-evidence,readme-polish}
feat/{audit-phase0,audit-phase1-temp,audit-phase1,cbor-minimal,cli-cloud-codex,cloud-codex,cloud-codex-apex,consolidate-all-phases,dispatch-f3-cutover,dispatch-planner,dispatch-tui-dashboard,driver-http,dx-scorecard-criterion,ebpf-loader,engine-a2a,event-sourcing,forge-daemon-f5-2026-06-30,g3-sharecli-spawn-2026-06-30,g3-substrate-throttle,gateway-{ansi-color,base64,bitfield,bitset,bloom,budget,bytes,...}}
(plus many more gateway-* branches and AIRLOCK archive branches not enumerated)
```

**Heaviest repo in scope.** 100 branches include:
- 2 `airlock-archive/wave4/*` tarball snapshots
- 3 `archive/thegent-dispatch/*` absorbed sub-repo branches
- `chore/release-v0.3.*` release branches
- `chore/rebase-substrate-*` rebase work branches
- 30+ `feat/gateway-*` feature branches
- `dependabot/*` automated dependency bumps
- `cursor/*` AI-assist session branches

### substrate-adapters-bundle (7 branches)

```
main
review/ownership-20260722-approved-next
review/ownership-20260722-pheno-agents-md
review/ownership-20260722-pheno-context
review/ownership-20260722-pheno-otel
review/ownership-20260722-phenoUtils
review/ownership-20260722-substrate-config
```

The 6 `review/ownership-20260722-*` branches indicate a recent ownership/governance audit on 2026-07-22; all merged into `main` per branch naming pattern.

## STATE — current branches

100 vs 7 branches; ZERO overlap. Both repos publicly accessible.

## ABSORBED — confirmed content states

- **substrate-adapters-bundle** is a meta-repo (per its description). It does NOT contain the substrate adapter crates itself; it points at them via git-submodule references and a curated README list.

## SUPERSEDES — receipts preserved

Neither repo is an archive of the other. Both retain full history independently.

## PROPOSED MUTATIONS (NOT EXECUTED — pending approval)

1. `substrate` → squash to 1 commit on `main` (preserve branch metadata in commit body).
2. `substrate-adapters-bundle` → squash to 1 commit on `main`.

**WARNING — HIGHEST branch count in scope**:
- 100 branches on `substrate`, including 2 tarball snapshots, 3 archive branches, 30+ gateway features, dependabot, cursor session branches, etc.
- A naive `git reset --soft` to 1 commit will **flatten ALL** of these into the single commit body. Branch metadata will be retained as text content; commit content may miss details.
- **Recommendation**: Before squash, run `git for-each-ref refs/heads/ --format='%(refname:short) %(objectname:short) %(committerdate:short) %(subject)' > branches-pre-squash.txt` and stash that file in `AgilePlus/docs/airlock/substrate-branches-manifest-pre-squash-2026-07-29.txt`. This is the receipt.

## LOCAL CHECKOUT COVERAGE

- ❌ Neither repo has a local clone.
- All 100 branches live on `origin`; no risk of local loss.
- Shallow clone of both required before any mutation (or API-only operations).

## RISK CLASS

**Low (for collision), HIGH (for squash complexity).**
- Branch-collision scan: clean.
- Squash complexity: 100-branch manifest + tarball snapshots requires careful receipt-keeping before merge.

## NEXT CHECKPOINT

User must approve:
- (a) shallow-clone of both repos for receipt-keeping
- (b) branches-manifest export before squash
- (c) final squash of each to 1 commit on `main`
