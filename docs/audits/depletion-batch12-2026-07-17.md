# Depletion Batch 12 — Delete Proposals (2026-07-17)

## Summary

| Category | Count |
|---|---|
| `H:RECOVERY_SNAPSHOT` | 1 |
| | _404-preservation snapshots of deleted/failed repos — content already preserved elsewhere_ |
| `I:NON_PHENOTYPE` | 9 |
| | _Game mods, course work, fitness apps — unrelated to Phenotype_ |
| **TOTAL** | **10** |

## Repositories proposed for deletion

| # | Repo | Category | Deletion Safety |
|---|---|---|---|
|  1 | `tracera-pr-worktree-20260703-0014-archive-2026-07-14` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |
|  2 | `472-P2-Flame-War` | `I:NON_PHENOTYPE` | 🟢 SAFE |
|  3 | `4sgm` | `I:NON_PHENOTYPE` | 🟢 SAFE |
|  4 | `Compound-Spheres-3D` | `I:NON_PHENOTYPE` | 🟢 SAFE |
|  5 | `Compound-Spheres-3D-Backup` | `I:NON_PHENOTYPE` | 🟢 SAFE |
|  6 | `P2` | `I:NON_PHENOTYPE` | 🟢 SAFE |
|  7 | `Project-Spyn` | `I:NON_PHENOTYPE` | 🟢 SAFE |
|  8 | `QuadSGM` | `I:NON_PHENOTYPE` | 🟢 SAFE |
|  9 | `RIP-Fitness-App` | `I:NON_PHENOTYPE` | 🟢 SAFE |
| 10 | `UnityDoorstop-NexusPatched` | `I:NON_PHENOTYPE` | 🟢 SAFE |

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

- [ ] Batch 12 reviewed and approved by Koosha
- [ ] `gh repo delete KooshaPari/<name> -y` for each repo
- [ ] Update `registry/disposition-index.json` with deletion timestamp
- [ ] Update `docs/audits/depletion-progress-2026-07-17.md`

## Cross-references

- Final classification: `docs/audits/final-exclusive-classification-2026-07-17.md`
- Registry: `registry/disposition-index.json`
- Batch 1: `docs/audits/depletion-batch1-2026-07-17.md`
