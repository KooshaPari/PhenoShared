# Airlock Decision: heliosHarness → KooshaPari/helios-cli

**Decision:** Absorbed into [`KooshaPari/helios-cli`](https://github.com/KooshaPari/helios-cli) as the `harness_recorder` crate + HeliosCLI workspace. No recreation needed.
**Decision date:** 2026-07-14
**Decision author:** Forge (automated inventory + absorption probe)

---

## Airlock metadata

| field | value |
|---|---|
| airlock id | `26ffbedabd25` |
| original upstream | `github.com/KooshaPari/heliosHarness.git` (now MISSING on GitHub) |
| bare mirror | `/Users/kooshapari/.airlock/repos/26ffbedabd25.git/` |
| worktree | `/Users/kooshapari/.airlock/worktrees/26ffbedabd25/` |
| canonical working_path | `heliosHarness/` |
| local working_path on disk | **NO** (folder absent from `~/CodeProjects/Phenotype/repos/`) |
| default branch | `master` @ `44c01d3` |
| refs/heads in bare mirror | **15** (incl. `master`, `main`, `gh-pages`, `lane-b/*`, `replay/*`, `keep-helios-cli-fork`) |
| most-recent branch | `lane-b/heliosHarness-20260226-115450` @ 2026-02-26 |
| latest run in state.sqlite | `replay/gh-pages-20260225-054046` → `d455834` (superseded=0) |
| state.sqlite last_sync | 2026-03-24 |

**Upstream classification (gh CLI as KooshaPari):** `missing_or_deleted`.

---

## Absorption target

**Primary target:** [`KooshaPari/helios-cli`](https://github.com/KooshaPari/helios-cli) — already the live local checkout at `~/CodeProjects/Phenotype/repos/helios-cli/` on branch `chore/absorb-helioscli-final-2026-06-20`. Note: the canonical airlock entry for helios-cli itself is `fed12af11b16`, NOT `f2270c66ee9d` (the abandoned `heliosCLI` duplicate).

---

## Evidence chain

| signal | source | finding |
|---|---|---|
| **External absorption commits** | `KooshaPari/helios-cli` commit history | `2026-06-20` × 3 commits: *"feat(absorb): merge HeliosCLI workspace (20 crates + root config + 9 dirs) into helios-cli"* / *"feat(absorb): complete HeliosCLI absorption"* / *"feat(absorb): add CHANGELOG.md + justfile from HeliosCLI final wave"*. |
| **harness_recorder lineage** | `KooshaPari/helios-cli` commit history | `2026-06-23`: *"feat(harness_recorder): absorb KLA (KommandLineAutomation) as harness_recorder crate (L5-200)"* — the harness functionality was rescued into this crate. |
| **Self-confessed intent** | `26ffbedabd25.git` commit history | `2026-02-23`: *"chore: Remove old clones/codex, keep helios-cli fork"* — author had already declared helios-cli the canonical home. |
| **Local receipt** | `git -C /Users/kooshapari/CodeProjects/Phenotype/repos/helios-cli/` | Current branch `chore/absorb-helioscli-final-2026-06-20` — branch name itself is the absorption manifest. |

**Conclusion:** `helios-cli` already absorbed the heliosHarness workspace via the L5-200 wave in June 2026. The airlock mirror holds pre-absorption recovery branches that would integrate as supplemental cleanup.

---

## Action plan

1. ✅ Mark-as-merged decision recorded here.
2. ⏭️ Push eligible branches from `26ffbedabd25.git` to `KooshaPari/helios-cli` as `airlock-recovery/<branch>`. **Skip `gh-pages`** (auto-generated, would create a junk-pages site). Branches already on `helios-cli` are skipped.
3. ⏭️ After push, `~/CodeProjects/Phenotype/repos/helios-cli/` remains the canonical checkout — recovery branches surface any net-new work pre-absorption.

---

## Rollback

```bash
for branch in $(gh api repos/KooshaPari/helios-cli/branches --paginate \
                 --jq '.[] | select(.name | startswith("airlock-recovery/")) | .name'); do
  echo "deleting ${branch}"
  gh api -X DELETE "repos/KooshaPari/helios-cli/git/refs/heads/${branch}" || true
done
```

(Note: rollback does NOT touch the local `helios-cli/` checkout or the existing `chore/absorb-helioscli-final-2026-06-20` branch — those predate this recovery push.)

---

## Cross-references

| artifact | location |
|---|---|
| airlock bare mirror | `/Users/kooshapari/.airlock/repos/26ffbedabd25.git/` |
| airlock worktree | `/Users/kooshapari/.airlock/worktrees/26ffbedabd25/` (detached HEAD) |
| local canonical checkout | `/Users/kooshapari/CodeProjects/Phenotype/repos/helios-cli/` (active) |
| full airlock inventory | `~/CodeProjects/Phenotype/repos/.airlock-inventory-2026-07-14.json` |
| absorption probe | `~/CodeProjects/Phenotype/repos/.airlock-absorption-probe-2026-07-14.json` |
| remote backup | https://gist.github.com/KooshaPari/3e6038adbfc4fe4c38965d02d0fc867e |
| probe scripts (re-runnable) | `~/CodeProjects/Phenotype/repos/_airlock-inventory-probe.py`, `~/CodeProjects/Phenotype/repos/_airlock-absorption-probe.py` |
| upstream URL (gone) | https://github.com/KooshaPari/heliosHarness |
| absorption target | https://github.com/KooshaPari/helios-cli |
