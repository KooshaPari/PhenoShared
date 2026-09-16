# Airlock decision — 2026-07-14 — Duplicate-pair disambiguation

**airlock id:** `1a5895a56a55`
**canonical local folder:** `cliproxyapi-plusplus`
**upstream URL:** `https://github.com/KooshaPari/cliproxyapi-plusplus.git`
**bare mirror:** `/Users/kooshapari/.airlock/repos/1a5895a56a55.git/`
**worktree:**    `/Users/kooshapari/.airlock/worktrees/1a5895a56a55/`

---

## Verdict

**Marked `CANONICAL-PAIR` — keep in airlock as live working quarantine.**

The companion entry `afe7b47b9c14` (folder `cliproxyapi++`) is the abandoned-duplicate; **this** entry is the canonical surviving half of the duplicate pair, because it has a live local checkout at `~/CodeProjects/Phenotype/repos/cliproxyapi-plusplus/` on branch `main` (HEAD `e72503ad2`).

---

## Evidence (cross-reference)

| half of pair | airlock id | local checkout | bare refs | status |
|---|---|---|---|---|
| **this (canonical)** | `1a5895a56a55` | `cliproxyapi-plusplus/` on `main` @ `e72503ad2` | 264 | **KEEP** |
| abandoned-duplicate | `afe7b47b9c14` | (none) | 255 | archive + prune |

See: `_phenofleet-decisions/airlock-decisions/2026-07-14-afe7b47b9c14-cliproxyapi++-abandoned-duplicate.md`

---

## Action plan

- ✅ Keep this airlock entry running — it's the active quarantine for the canonical local repo
- ✅ Cross-reference link established in INDEX.md
- ⏸ **DO NOT prune** — operator-driven only

## Cross-references

- Inventory probe JSON: `_phenofleet-decisions/airlock-decisions/.airlock-inventory-2026-07-14.json`
- Remote backup gist: https://gist.github.com/KooshaPari/3e6038adbfc4fe4c38965d02d0fc867e
