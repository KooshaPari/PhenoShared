# Depletion Batch 14 — Delete Proposals (2026-07-17)

## Summary

| Category | Count |
|---|---|
| `D:TOO_BOUND_UPSTREAM` | 10 |
| | _Forks of upstream projects — replaceable from upstream_ |
| **TOTAL** | **10** |

## Repositories proposed for deletion

| # | Repo | Category | Deletion Safety |
|---|---|---|---|
|  1 | `bifrost` | `D:TOO_BOUND_UPSTREAM` | 🟡 REVIEW |
|  2 | `cliproxyapi-plusplus` | `D:TOO_BOUND_UPSTREAM` | 🟡 REVIEW |
|  3 | `context-mode-plusplus` | `D:TOO_BOUND_UPSTREAM` | 🟡 REVIEW |
|  4 | `grapheon-bindings` | `D:TOO_BOUND_UPSTREAM` | 🟡 REVIEW |
|  5 | `nanovms` | `D:TOO_BOUND_UPSTREAM` | 🟡 REVIEW |
|  6 | `netweave-3` | `D:TOO_BOUND_UPSTREAM` | 🟡 REVIEW |
|  7 | `netweave-final2` | `D:TOO_BOUND_UPSTREAM` | 🟡 REVIEW |
|  8 | `phench` | `D:TOO_BOUND_UPSTREAM` | 🟡 REVIEW |
|  9 | `phenotype-go-kit` | `D:TOO_BOUND_UPSTREAM` | 🟡 REVIEW |
| 10 | `phenotype-infrakit` | `D:TOO_BOUND_UPSTREAM` | 🟡 REVIEW |

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

- [ ] Batch 14 reviewed and approved by Koosha
- [ ] `gh repo delete KooshaPari/<name> -y` for each repo
- [ ] Update `registry/disposition-index.json` with deletion timestamp
- [ ] Update `docs/audits/depletion-progress-2026-07-17.md`

## Cross-references

- Final classification: `docs/audits/final-exclusive-classification-2026-07-17.md`
- Registry: `registry/disposition-index.json`
- Batch 1: `docs/audits/depletion-batch1-2026-07-17.md`
