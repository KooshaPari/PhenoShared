# Airlock decision — 2026-07-14 — Duplicate-pair disambiguation

**airlock id:** `f2270c66ee9d`
**canonical local folder:** `heliosCLI`
**upstream URL:** `https://github.com/KooshaPari/helios-cli.git`
**bare mirror:** `/Users/kooshapari/.airlock/repos/f2270c66ee9d.git/`
**worktree:**    `/Users/kooshapari/.airlock/worktrees/f2270c66ee9d/`

---

## Verdict

**Marked `ABANDONED-DUPLICATE` — safe to prune after archive.**

The canonical home for this upstream is the airlock entry `fed12af11b16` (local folder `helios-cli`). The local checkout on `~/CodeProjects/Phenotype/repos/helios-cli/` is currently at branch `chore/absorb-helioscli-final-2026-06-20` (commit `ae2f311`) — live working repository. This entry's bare mirror is a parallel quarantine under a different `working_path` string (`heliosCLI` vs `helios-cli`) with no local working copy.

---

## Evidence

| signal | `fed12af11b16` (`helios-cli`) ← CANONICAL | `f2270c66ee9d` (`heliosCLI`) ← this one |
|---|---|---|
| upstream URL | `github.com/KooshaPari/helios-cli.git` | (same) |
| bare refs/heads count | 1300 (large upstream-synced fork) | 1293 |
| local path on disk | **yes** — branch `chore/absorb-helioscli-final-2026-06-20` @ `ae2f311` | **NO** — never checked out |
| runs (total / active) | 81 / 77 | 111 / 99 |
| latest run | branch unspecified, head_sha unspecified | branch unspecified, head_sha unspecified |
| bare last_sync | recent | recent |

**Reason for being canonical:** the local checkout on `~/CodeProjects/Phenotype/repos/helios-cli/` is the working repository AND is on a branch explicitly named `chore/absorb-helioscli-final-2026-06-20` — meaning the local branch literally records the absorption event. The bare mirror at `f2270c66ee9d.git/` is a side-effect of the airlock having once tried to maintain two parallel quarantines for the same upstream under differing `working_path` strings (`heliosCLI` capitalized vs `helios-cli` lowercase-dashed).

---

## Action plan

1. ✅ Tarball the bare mirror + worktree to `_phenofleet-decisions/airlock-archived/f2270c66ee9d.{git,tree}.tar.zst`
2. ✅ Compute SHA256 of each tarball
3. ✅ Verify each tarball roundtrips correctly (extract → `git for-each-ref` matches)
4. ✅ Write SHA256 manifest to `_phenofleet-decisions/airlock-archived/SHA256SUMS.txt`
5. ✅ Install `READY_TO_PRUNE.md` sentinel inside `/Users/kooshapari/.airlock/repos/f2270c66ee9d.git/` (does NOT delete)
6. ⏸ **DO NOT delete** — require explicit operator action

### Companion recovery decision

The 1293 branches in this bare mirror are NOT pushed to `KooshaPari/helios-cli` (already-canonical fork with 1300 branches). They live only in the airlock. After archive, if the canonical local checkout (`fed12af11b16`) shows branch X missing, the operator can pull X from the tarball.

---

## Cross-references

- Inventory probe JSON: `_phenofleet-decisions/airlock-decisions/.airlock-inventory-2026-07-14.json`
- Absorption probe JSON: `.airlock-absorption-probe-2026-07-14.json`
- Companion decision (canonical): `_phenofleet-decisions/airlock-decisions/2026-07-14-fed12af11b16-helios-cli-canonical.md` (sibling note in INDEX.md)
- Decision for absorbed mirror: `_phenofleet-decisions/airlock-decisions/2026-07-14-26ffbedabd25-heliosHarness-absorbed-into-helios-cli.md` (this is the absorbed→helios-cli decision, distinct from this duplicate-cleanup decision)
- Remote backup gist: https://gist.github.com/KooshaPari/3e6038adbfc4fe4c38965d02d0fc867e

## Rollback (if this decision is later reversed)

1. Restore the tarball: `tar --zstd -xf _phenofleet-decisions/airlock-archived/f2270c66ee9d.git.tar.zst -C /tmp/restore/`
2. Move it back: `mv /tmp/restore/f2270c66ee9d.git /Users/kooshapari/.airlock/repos/`
3. Remove sentinel: `rm /Users/kooshapari/.airlock/repos/f2270c66ee9d.git/READY_TO_PRUNE.md`
4. Re-run the inventory probe to confirm state restoration.
