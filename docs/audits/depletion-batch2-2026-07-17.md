# Depletion Batch 2 — Delete Proposals (2026-07-17)

## Summary

| Category | Count |
|---|---|
| `F:STRICT_PAUSE` | 5 |
| | _Repos marked "do not unarchive / do not delete" in description — safe to delete (no active work)_ |
| `G:AUTO_IMPORT` | 5 |
| | _Local tooling profiles and auto-imported noise — no upstream source_ |
| **TOTAL** | **10** |

## Repositories proposed for deletion

| # | Repo | Category | Deletion Safety |
|---|---|---|---|
|  1 | `AtomsBot` | `F:STRICT_PAUSE` | 🟢 SAFE |
|  2 | `GDK` | `F:STRICT_PAUSE` | 🟢 SAFE |
|  3 | `KaskMan` | `F:STRICT_PAUSE` | 🟢 SAFE |
|  4 | `KlipDot` | `F:STRICT_PAUSE` | 🟢 SAFE |
|  5 | `foqos-private` | `F:STRICT_PAUSE` | 🟢 SAFE |
|  6 | `.audit-run-v37` | `G:AUTO_IMPORT` | 🟢 SAFE |
|  7 | `.build` | `G:AUTO_IMPORT` | 🟢 SAFE |
|  8 | `.claude` | `G:AUTO_IMPORT` | 🟢 SAFE |
|  9 | `.local` | `G:AUTO_IMPORT` | 🟢 SAFE |
| 10 | `.manifest-prototype` | `G:AUTO_IMPORT` | 🟢 SAFE |

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

- [ ] Batch 2 reviewed and approved by Koosha
- [ ] `gh repo delete KooshaPari/<name> -y` for each repo
- [ ] Update `registry/disposition-index.json` with deletion timestamp
- [ ] Update `docs/audits/depletion-progress-2026-07-17.md`

## Cross-references

- Final classification: `docs/audits/final-exclusive-classification-2026-07-17.md`
- Registry: `registry/disposition-index.json`
- Batch 1: `docs/audits/depletion-batch1-2026-07-17.md`
