# Depletion Batch 4 — Delete Proposals (2026-07-17)

## Summary

| Category | Count |
|---|---|
| `G:AUTO_IMPORT` | 10 |
| | _Local tooling profiles and auto-imported noise — no upstream source_ |
| **TOTAL** | **10** |

## Repositories proposed for deletion

| # | Repo | Category | Deletion Safety |
|---|---|---|---|
|  1 | `benchmark` | `G:AUTO_IMPORT` | 🟢 SAFE |
|  2 | `benchmarks` | `G:AUTO_IMPORT` | 🟢 SAFE |
|  3 | `coverage` | `G:AUTO_IMPORT` | 🟢 SAFE |
|  4 | `crates` | `G:AUTO_IMPORT` | 🟢 SAFE |
|  5 | `curated-traces` | `G:AUTO_IMPORT` | 🟢 SAFE |
|  6 | `dist` | `G:AUTO_IMPORT` | 🟢 SAFE |
|  7 | `docs` | `G:AUTO_IMPORT` | 🟢 SAFE |
|  8 | `go` | `G:AUTO_IMPORT` | 🟢 SAFE |
|  9 | `kernels` | `G:AUTO_IMPORT` | 🟢 SAFE |
| 10 | `logs` | `G:AUTO_IMPORT` | 🟢 SAFE |

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

- [ ] Batch 4 reviewed and approved by Koosha
- [ ] `gh repo delete KooshaPari/<name> -y` for each repo
- [ ] Update `registry/disposition-index.json` with deletion timestamp
- [ ] Update `docs/audits/depletion-progress-2026-07-17.md`

## Cross-references

- Final classification: `docs/audits/final-exclusive-classification-2026-07-17.md`
- Registry: `registry/disposition-index.json`
- Batch 1: `docs/audits/depletion-batch1-2026-07-17.md`
