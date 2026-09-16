# Depletion Batch 7 — Delete Proposals (2026-07-17)

## Summary

| Category | Count |
|---|---|
| `H:RECOVERY_SNAPSHOT` | 10 |
| | _404-preservation snapshots of deleted/failed repos — content already preserved elsewhere_ |
| **TOTAL** | **10** |

## Repositories proposed for deletion

| # | Repo | Category | Deletion Safety |
|---|---|---|---|
|  1 | `Parpoura-archive` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |
|  2 | `Repos-phenodocs-uncommitted-2026-07-15` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |
|  3 | `Repos-phenotype-handbook-2026-07-15` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |
|  4 | `Repos-phenotype-journeys-2026-07-15` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |
|  5 | `Repos-phenotype-omlx-2026-07-15` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |
|  6 | `Repos-phenotype-router-spec-2026-07-15` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |
|  7 | `Repos-phenotype-shared-2026-07-15` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |
|  8 | `Repositories-orphan-snapshots-2026-07-14` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |
|  9 | `Repositories-orphan-snapshots-2026-07-15` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |
| 10 | `ResilienceKit-archive` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |

## Why these are deletable

These repos fall outside the 64-repo canonical ecosystem (9 SPINE + 1 FOCUSED_PRIMITIVE + 54 WORKING). They have already been:

- **Audited in depth** (see `docs/audits/final-exclusive-classification-2026-07-17.md`)
- **Classified** into one of the 10 mutually-exclusive disposition categories
- **Tombstoned** in `registry/disposition-index.json` (fsm=archived or never_existed)

## Restoration path

If any of these repos need to be recovered from deletion:

```bash
# Restore via git reflog (within 30 days of deletion)
gh repo restore KooshaPari/<name>

# Or contact GitHub support for hard-deleted repos (>30 days)
```

## Executed

- [ ] Batch 7 reviewed and approved by Koosha
- [ ] `gh repo delete KooshaPari/<name> -y` for each repo
- [ ] Update `registry/disposition-index.json` with deletion timestamp
- [ ] Update `docs/audits/depletion-progress-2026-07-17.md`

## Cross-references

- Final classification: `docs/audits/final-exclusive-classification-2026-07-17.md`
- Registry: `registry/disposition-index.json`
- Batch 1: `docs/audits/depletion-batch1-2026-07-17.md`
