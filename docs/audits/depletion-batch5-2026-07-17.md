# Depletion Batch 5 — Delete Proposals (2026-07-17)

## Summary

| Category | Count |
|---|---|
| `G:AUTO_IMPORT` | 10 |
| | _Local tooling profiles and auto-imported noise — no upstream source_ |
| **TOTAL** | **10** |

## Repositories proposed for deletion

| # | Repo | Category | Deletion Safety |
|---|---|---|---|
|  1 | `omniroute-rs` | `G:AUTO_IMPORT` | 🟢 SAFE |
|  2 | `omniroute-rt` | `G:AUTO_IMPORT` | 🟢 SAFE |
|  3 | `omniroute-rust` | `G:AUTO_IMPORT` | 🟢 SAFE |
|  4 | `pheno-predict-archive-2026-07-14` | `G:AUTO_IMPORT` | 🟢 SAFE |
|  5 | `rust` | `G:AUTO_IMPORT` | 🟢 SAFE |
|  6 | `scripts` | `G:AUTO_IMPORT` | 🟢 SAFE |
|  7 | `sessions` | `G:AUTO_IMPORT` | 🟢 SAFE |
|  8 | `template-commons` | `G:AUTO_IMPORT` | 🟢 SAFE |
|  9 | `tracera-2-archived` | `G:AUTO_IMPORT` | 🟢 SAFE |
| 10 | `work` | `G:AUTO_IMPORT` | 🟢 SAFE |

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

- [ ] Batch 5 reviewed and approved by Koosha
- [ ] `gh repo delete KooshaPari/<name> -y` for each repo
- [ ] Update `registry/disposition-index.json` with deletion timestamp
- [ ] Update `docs/audits/depletion-progress-2026-07-17.md`

## Cross-references

- Final classification: `docs/audits/final-exclusive-classification-2026-07-17.md`
- Registry: `registry/disposition-index.json`
- Batch 1: `docs/audits/depletion-batch1-2026-07-17.md`
