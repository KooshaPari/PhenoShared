# Plan: Worktree Remediation

## Retirement Summary (2026-05-05)
Work was verified completed ops — retired as COMPLETED_OPS.

## Work Performed (2026-03-28/29)

- [x] Archive 9 legacy *-wtrees directories to `archive/legacy-wtrees/2026-03-28/`
- [x] Implement `worktree_governance_inventory.py` with conformance checks
- [x] Implement `worktree_legacy_remediation_report.py` with legacy detection
- [x] Implement `worktree_governance.sh` shell wrapper
- [x] Clean up orphaned `phenotype-gauge-wtrees` directory
- [x] Stash WIP changes in `thegent-wtrees/rebase-fix-cache-test-pyright`

## Verification
- Governance tests: 10/10 passing
- Shell script: executable with `check`/`prune`/`migrate` commands

## Superseded By
Live worktree governance now embedded in:
- Phenotype/CLAUDE.md "Worktree Rule"
- repos/CLAUDE.md worktree discipline
- repos/.worktrees/ + repos/`<repo>`-wtrees/`<topic>` conventions
