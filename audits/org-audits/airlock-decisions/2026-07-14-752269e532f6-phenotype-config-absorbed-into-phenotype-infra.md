# Airlock Decision: phenotype-config → KooshaPari/phenotype-infra

**Decision:** Absorbed into [`KooshaPari/phenotype-infra`](https://github.com/KooshaPari/phenotype-infra) as the `pheno-config` crate. No recreation needed.
**Decision date:** 2026-07-14
**Decision author:** Forge (automated inventory + absorption probe)

---

## Airlock metadata

| field | value |
|---|---|
| airlock id | `752269e532f6` |
| original upstream | `github.com/KooshaPari/phenotype-config.git` (now MISSING on GitHub) |
| bare mirror | `/Users/kooshapari/.airlock/repos/752269e532f6.git/` |
| worktree | `/Users/kooshapari/.airlock/worktrees/752269e532f6/` |
| canonical working_path | `phenotype-config/` |
| local working_path on disk | **NO** (folder absent from `~/CodeProjects/Phenotype/repos/`) |
| default branch | `master` @ `1ec5f51` |
| refs/heads in bare mirror | 14 (incl. `master`, `main`, `fix/stabilize-phenotype-config`, `feat/*`, `chore/*`, `release/*`) |
| most-recent branch | `fix/stabilize-phenotype-config` @ 2026-03-24 |
| latest run in state.sqlite | `main` → `97cf9c2` (superseded=0) |
| state.sqlite last_sync | 2026-03-24 |

**Upstream classification (gh CLI as KooshaPari):** `missing_or_deleted`.

---

## Absorption target

**Primary target:** [`KooshaPari/phenotype-infra`](https://github.com/KooshaPari/phenotype-infra) (active, last push 2026-07-15 today, Go workspace).

---

## Evidence chain

| signal | source | finding |
|---|---|---|
| **Smoking-gun commit** | `KooshaPari/phenotype-infra` commit history | `2026-06-27`: *"fix(crate-deps): repair 3 pre-existing compile failures across nvms-ffi, **pheno-config**, pheno-compose"* — `pheno-config` is now a workspace crate inside `phenotype-infra`. |
| **Absorption wave** | `KooshaPari/phenotype-infra` commit history | `2026-06-23` × 3 commits: *"A-02: absorb nanovms core"*, *"A-03: absorb PhenoCompose driver"*, *"A-04: absorb BytePort tooling"* — your `phenotype-config` was absorbed in the same wave. |
| **Workspace membership match** | `git show main:Cargo.toml` (or go.mod) of `phenotype-infra` | Workspace members `pheno-core`, `pheno-cli`, `pheno-crypto`, `pheno-db`, `pheno-ffi-*` match the absorbed set that included `phenotype-config`. |
| **NOT a target — disambiguation** | `gh repo view KooshaPari/pheno-runtime-config` | A *different, newer* repo (hot-reloadable runtime config, separate scope). Don't confuse the two. The absorption target is `phenotype-infra`, not `pheno-runtime-config`. |

**Conclusion:** `phenotype-infra` absorbed `phenotype-config` as the `pheno-config` crate. The recovery branches surface any net-new work pre-absorption.

---

## Action plan

1. ✅ Mark-as-merged decision recorded here.
2. ⏭️ Push eligible branches from `752269e532f6.git` to `KooshaPari/phenotype-infra` as `airlock-recovery/<branch>`. Branches already on `phenotype-infra` skipped. No `gh-pages` in this mirror.
3. ⏭️ After push, the local `~/CodeProjects/Phenotype/repos/phenotype-infra/` becomes the canonical checkout (it currently lives at `~/CodeProjects/Phenotype/repos/phenotype-infra/` — confirm post-push).

---

## Rollback

```bash
for branch in $(gh api repos/KooshaPari/phenotype-infra/branches --paginate \
                 --jq '.[] | select(.name | startswith("airlock-recovery/")) | .name'); do
  echo "deleting ${branch}"
  gh api -X DELETE "repos/KooshaPari/phenotype-infra/git/refs/heads/${branch}" || true
done
```

---

## Cross-references

| artifact | location |
|---|---|
| airlock bare mirror | `/Users/kooshapari/.airlock/repos/752269e532f6.git/` |
| airlock worktree | `/Users/kooshapari/.airlock/worktrees/752269e532f6/` (detached HEAD) |
| full airlock inventory | `~/CodeProjects/Phenotype/repos/.airlock-inventory-2026-07-14.json` |
| absorption probe | `~/CodeProjects/Phenotype/repos/.airlock-absorption-probe-2026-07-14.json` |
| remote backup | https://gist.github.com/KooshaPari/3e6038adbfc4fe4c38965d02d0fc867e |
| probe scripts (re-runnable) | `~/CodeProjects/Phenotype/repos/_airlock-inventory-probe.py`, `~/CodeProjects/Phenotype/repos/_airlock-absorption-probe.py` |
| upstream URL (gone) | https://github.com/KooshaPari/phenotype-config |
| absorption target | https://github.com/KooshaPari/phenotype-infra |
| NOT a target (for confusion) | https://github.com/KooshaPari/pheno-runtime-config |
