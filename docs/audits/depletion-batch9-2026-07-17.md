# Depletion Batch 9 — Delete Proposals (2026-07-17)

## Summary

| Category | Count |
|---|---|
| `H:RECOVERY_SNAPSHOT` | 10 |
| | _404-preservation snapshots of deleted/failed repos — content already preserved elsewhere_ |
| **TOTAL** | **10** |

## Repositories proposed for deletion

| # | Repo | Category | Deletion Safety |
|---|---|---|---|
|  1 | `airlock-v2-smoke-test-90007` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |
|  2 | `apikit-httpora-final-archive-2026-07-14` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |
|  3 | `chatta-archive-2026-07-14` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |
|  4 | `dinoforge-packs-archive-2026-07-14` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |
|  5 | `docs-site-archive-2026-07-14` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |
|  6 | `focalpoint-orphan-snapshot-2026-07-14` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |
|  7 | `forge-AgilePlus` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |
|  8 | `home-recovery-2026-07` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |
|  9 | `home-recovery-2026-07-archive` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |
| 10 | `hwLedger` | `H:RECOVERY_SNAPSHOT` | 🟡 REVIEW |

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

- [ ] Batch 9 reviewed and approved by Koosha
- [ ] `gh repo delete KooshaPari/<name> -y` for each repo
- [ ] Update `registry/disposition-index.json` with deletion timestamp
- [ ] Update `docs/audits/depletion-progress-2026-07-17.md`

## Cross-references

- Final classification: `docs/audits/final-exclusive-classification-2026-07-17.md`
- Registry: `registry/disposition-index.json`
- Batch 1: `docs/audits/depletion-batch1-2026-07-17.md`
