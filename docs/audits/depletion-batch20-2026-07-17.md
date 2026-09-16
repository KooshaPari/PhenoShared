# Depletion Batch 20 — Delete Proposals (2026-07-17)

## Summary

| Category | Count |
|---|---|
| `C:TOO_LARGE_RETIRE` | 10 |
| | _Too large in scope to absorb — unmanageable as standalone repos_ |
| **TOTAL** | **10** |

## Repositories proposed for deletion

| # | Repo | Category | Deletion Safety |
|---|---|---|---|
|  1 | `eyetracker` | `C:TOO_LARGE_RETIRE` | 🟡 REVIEW |
|  2 | `forgecode` | `C:TOO_LARGE_RETIRE` | 🟡 REVIEW |
|  3 | `heliosBench` | `C:TOO_LARGE_RETIRE` | 🟡 REVIEW |
|  4 | `hexa-kit` | `C:TOO_LARGE_RETIRE` | 🟡 REVIEW |
|  5 | `kmobile` | `C:TOO_LARGE_RETIRE` | 🟡 REVIEW |
|  6 | `localbase3` | `C:TOO_LARGE_RETIRE` | 🟡 REVIEW |
|  7 | `pheno-org-audits` | `C:TOO_LARGE_RETIRE` | 🟡 REVIEW |
|  8 | `phenoDesign` | `C:TOO_LARGE_RETIRE` | 🟡 REVIEW |
|  9 | `phenoDesign-archive` | `C:TOO_LARGE_RETIRE` | 🟡 REVIEW |
| 10 | `phenoResearchEngine` | `C:TOO_LARGE_RETIRE` | 🟡 REVIEW |

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

- [ ] Batch 20 reviewed and approved by Koosha
- [ ] `gh repo delete KooshaPari/<name> -y` for each repo
- [ ] Update `registry/disposition-index.json` with deletion timestamp
- [ ] Update `docs/audits/depletion-progress-2026-07-17.md`

## Cross-references

- Final classification: `docs/audits/final-exclusive-classification-2026-07-17.md`
- Registry: `registry/disposition-index.json`
- Batch 1: `docs/audits/depletion-batch1-2026-07-17.md`
