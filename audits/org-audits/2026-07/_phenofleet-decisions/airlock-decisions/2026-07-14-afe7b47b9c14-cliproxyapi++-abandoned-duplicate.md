# Airlock decision — 2026-07-14 — Duplicate-pair disambiguation

**airlock id:** `afe7b47b9c14`
**canonical local folder:** `cliproxyapi++`
**upstream URL:** `https://github.com/KooshaPari/cliproxyapi-plusplus.git`
**bare mirror:** `/Users/kooshapari/.airlock/repos/afe7b47b9c14.git/`
**worktree:**    `/Users/kooshapari/.airlock/worktrees/afe7b47b9c14/`

---

## Verdict

**Marked `ABANDONED-DUPLICATE` — safe to prune after archive.**

The canonical home for this upstream is the airlock entry `1a5895a56a55` (local folder `cliproxyapi-plusplus`). This entry's bare mirror is a strict subset of `1a5895…`'s and the local checkout never existed.

---

## Evidence

| signal | `1a5895a56a55` (`cliproxyapi-plusplus`) ← CANONICAL | `afe7b47b9c14` (`cliproxyapi++`) ← this one |
|---|---|---|
| upstream URL | `github.com/KooshaPari/cliproxyapi-plusplus.git` | (same) |
| bare refs/heads count | 264 | 255 |
| local path on disk | **yes** — branch `main` @ `e72503ad2` ("feat: upstream port") | **NO** — never checked out |
| runs (total / active) | 110 / 93 | 74 / 71 |
| latest run | branch unspecified, head_sha unspecified | branch unspecified, head_sha unspecified |
| bare last_sync | recent | recent |

**Reason for being canonical:** the local checkout on `~/CodeProjects/Phenotype/repos/cliproxyapi-plusplus/` is the working repository; this airlock entry has no local working copy. The bare mirror at `afe7b47b9c14.git/` is purely a side-effect of the airlock having once tried to maintain two parallel quarantines for the same upstream under different `working_path` strings.

---

## Action plan

1. ✅ Tarball the bare mirror + worktree to `_phenofleet-decisions/airlock-archived/afe7b47b9c14.{git,tree}.tar.zst`
2. ✅ Compute SHA256 of each tarball
3. ✅ Verify each tarball roundtrips correctly (extract → `git for-each-ref` matches)
4. ✅ Write SHA256 manifest to `_phenofleet-decisions/airlock-archived/SHA256SUMS.txt`
5. ✅ Install `READY_TO_PRUNE.md` sentinel inside `/Users/kooshapari/.airlock/repos/afe7b47b9c14.git/` (does NOT delete)
6. ⏸ **DO NOT delete** — require explicit operator action (`git -C ~/.airlock/repos/afe7b47b9c14.git/fsck && rm -rf`)

### Companion recovery decision

The 255 branches in this bare mirror are NOT pushed to `KooshaPari/cliproxyapi-plusplus`. They live only in the airlock. After archive:
- If the canonical local checkout (`1a5895a56a55`) shows branch X missing, the operator can pull X from the tarball:
  `git -C /path/to/archived/afe7b47b9c14.git branch X origin/airlock-recovery/X`

---

## Cross-references

- Inventory probe JSON: `_phenofleet-decisions/airlock-decisions/.airlock-inventory-2026-07-14.json` (cross-ref table)
- Absorption evidence JSON: `.airlock-absorption-probe-2026-07-14.json`
- Companion decision (canonical): `_phenofleet-decisions/airlock-decisions/2026-07-14-1a5895a56a55-cliproxyapi-plusplus-canonical.md` (sibling note in INDEX.md)
- Remote backup gist: https://gist.github.com/KooshaPari/3e6038adbfc4fe4c38965d02d0fc867e

## Rollback (if this decision is later reversed)

1. Restore the tarball: `tar --zstd -xf _phenofleet-decisions/airlock-archived/afe7b47b9c14.git.tar.zst -C /tmp/restore/`
2. Move it back: `mv /tmp/restore/afe7b47b9c14.git /Users/kooshapari/.airlock/repos/`
3. Remove sentinel: `rm /Users/kooshapari/.airlock/repos/afe7b47b9c14.git/READY_TO_PRUNE.md`
4. Re-run the inventory probe to confirm state restoration.
