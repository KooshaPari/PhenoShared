# Airlock decision — 2026-07-14 — Duplicate-pair disambiguation

**airlock id:** `fed12af11b16`
**canonical local folder:** `helios-cli`
**upstream URL:** `https://github.com/KooshaPari/helios-cli.git`
**bare mirror:** `/Users/kooshapari/.airlock/repos/fed12af11b16.git/`
**worktree:**    `/Users/kooshapari/.airlock/worktrees/fed12af11b16/`

---

## Verdict

**Marked `CANONICAL-PAIR` — keep in airlock as live working quarantine.**

The companion entry `f2270c66ee9d` (folder `heliosCLI`) is the abandoned-duplicate; **this** entry is the canonical surviving half, because it has a live local checkout at `~/CodeProjects/Phenotype/repos/helios-cli/` on branch `chore/absorb-helioscli-final-2026-06-20` (HEAD `ae2f311`) — the branch name itself records the absorption event.

---

## Evidence (cross-reference)

| half of pair | airlock id | local checkout | bare refs | status |
|---|---|---|---|---|
| **this (canonical)** | `fed12af11b16` | `helios-cli/` on `chore/absorb-helioscli-final-2026-06-20` @ `ae2f311` | 1300 | **KEEP** |
| abandoned-duplicate | `f2270c66ee9d` | (none) | 1293 | archive + prune |

See: `_phenofleet-decisions/airlock-decisions/2026-07-14-f2270c66ee9d-heliosCLI-abandoned-duplicate.md`

---

## Action plan

- ✅ Keep this airlock entry running — it's the active quarantine for the canonical local repo
- ✅ Cross-reference link established in INDEX.md
- ⏸ **DO NOT prune** — operator-driven only

## Cross-references

- Inventory probe JSON: `_phenofleet-decisions/airlock-decisions/.airlock-inventory-2026-07-14.json`
- Companion absorbed decision: `_phenofleet-decisions/airlock-decisions/2026-07-14-26ffbedabd25-heliosHarness-absorbed-into-helios-cli.md` (different decision — `heliosHarness` was a separate repo absorbed into this one)
- Remote backup gist: https://gist.github.com/KooshaPari/3e6038adbfc4fe4c38965d02d0fc867e
