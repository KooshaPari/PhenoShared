# Airlock Decision: tokenledger → KooshaPari/Tokn

**Decision:** Absorbed into [`KooshaPari/Tokn`](https://github.com/KooshaPari/Tokn) as a workspace crate. No recreation needed.
**Decision date:** 2026-07-14
**Decision author:** Forge (automated inventory + absorption probe)

---

## Airlock metadata

| field | value |
|---|---|
| airlock id | `004dc7b071f2` |
| original upstream | `github.com/KooshaPari/tokenledger.git` (now MISSING on GitHub) |
| bare mirror | `/Users/kooshapari/.airlock/repos/004dc7b071f2.git/` |
| worktree | `/Users/kooshapari/.airlock/worktrees/004dc7b071f2/` |
| canonical working_path | `tokenledger/` |
| local working_path on disk | **NO** (folder absent from `~/CodeProjects/Phenotype/repos/`) |
| default branch | `master` @ `b042e2c` |
| refs/heads in bare mirror | 14 (incl. `master`, `main`, `fix/*`, `feat/*`, `chore/*`, `policy/*`) |
| most-recent branch | `fix/stabilize-tokenledger` @ 2026-03-24 |
| latest run in state.sqlite | `policy/layered-pr-gate-20260227` → `d096796` (superseded=0) |
| state.sqlite last_sync | 2026-03-24 |

**Upstream classification (gh CLI as KooshaPari):** `missing_or_deleted` — GraphQL "Could not resolve to a Repository".

---

## Absorption target

**Primary target:** [`KooshaPari/Tokn`](https://github.com/KooshaPari/Tokn) (active, last push 2026-07-02)

---

## Evidence chain

| signal | source | finding |
|---|---|---|
| **README identity** | `git show main:README.md` in `004dc7b071f2.git` vs `gh api repos/KooshaPari/Tokn/contents/README.md` | First line of `Tokn` README: *"Enterprise-grade token management and pricing governance system for AI coding agents."* — byte-identical to `tokenledger`'s tagline. |
| **Workspace lineage** | `Tokn` README §Workspace | *"This is a Rust workspace with two main crates: `tokenledger` — Enterprise-grade token management … `ParetoRs` — Pareto-optimal cost engine …"* — `tokenledger` is literally preserved as a crate inside `Tokn`. |
| **Commit declaration** | `Tokn` commit history | Commit `2026-06-03`: *"docs: bump work-state — Tokn is canonical Rust routing substrate (tokenledger::routing) per ADR-001"*. |
| **No code loss** | bare mirror inspection | All 14 branches in `004dc7b071f2.git` are reachable from `master` or `main`; no orphaned objects. |
| **Target present & active** | `gh repo view KooshaPari/Tokn` | Returns valid metadata; not archived; not private; defaultBranchRef present. |

**Conclusion:** `Tokn` IS the renamed/expanded `tokenledger`. The original crate is preserved as a workspace member inside `Tokn`.

---

## Action plan

1. ✅ Mark-as-merged decision recorded here.
2. ⏭️ Push all eligible branches from `004dc7b071f2.git` to `KooshaPari/Tokn` as `airlock-recovery/<branch>`. Branches already present on `Tokn` will be skipped. `gh-pages` (if any) will be skipped — none in this mirror.
3. ⏭️ After push, mirror task to follow-up (id `004dc7b071f2` + `main`/`master` of `Tokn`) tracks recovery state. Local `~/CodeProjects/Phenotype/repos/Tokn/` becomes the canonical checkout.

---

## Rollback

To un-push the recovery branches if desired:
```bash
for branch in $(gh api repos/KooshaPari/Tokn/branches --paginate \
                 --jq '.[] | select(.name | startswith("airlock-recovery/")) | .name'); do
  branch_short=${branch#airlock-recovery/}
  echo "deleting airlock-recovery/${branch_short}"
  gh api -X DELETE "repos/KooshaPari/Tokn/git/refs/heads/${branch}" || true
done
```

---

## Cross-references

| artifact | location |
|---|---|
| airlock bare mirror | `/Users/kooshapari/.airlock/repos/004dc7b071f2.git/` |
| airlock worktree | `/Users/kooshapari/.airlock/worktrees/004dc7b071f2/` (detached HEAD — scratch) |
| full airlock inventory | `~/CodeProjects/Phenotype/repos/.airlock-inventory-2026-07-14.json` |
| absorption probe | `~/CodeProjects/Phenotype/repos/.airlock-absorption-probe-2026-07-14.json` |
| remote backup | https://gist.github.com/KooshaPari/3e6038adbfc4fe4c38965d02d0fc867e |
| probe scripts (re-runnable) | `~/CodeProjects/Phenotype/repos/_airlock-inventory-probe.py`, `~/CodeProjects/Phenotype/repos/_airlock-absorption-probe.py` |
| upstream URL (gone) | https://github.com/KooshaPari/tokenledger |
| absorption target | https://github.com/KooshaPari/Tokn |
