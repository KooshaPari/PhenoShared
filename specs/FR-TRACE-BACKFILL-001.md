# FR-TRACE-BACKFILL-001 — Backfill Missing Traceability Annotations

## Context

`scripts/traceability-check.py` currently reports 46 implemented specs in
`traceability.json` that lack `@trace <ID>` or literal FR-ID markers in
source/tests. While the backfill is in progress the gate runs in **soft
mode** (default, exits 0, prints `WARN: Missing <ID>` lines). The
original strict behavior is preserved behind `--strict-annotations` (see
PR referencing #168 / #54).

This FR tracks the remediation. Closing this FR flips the CI workflow
back to `--strict-annotations` and deletes the soft-mode banner.

## Gap Inventory (46 IDs)

| Repository             | Count | Notes                                         |
|------------------------|-------|-----------------------------------------------|
| phenotype-skills       | 8     | `SKILL-*` markers pending                     |
| task-engine            | 6     | `TASK-*` markers pending                      |
| nanovms                | 10    | `VM-*` markers pending (largest chunk)        |
| thegent                | 6     | mixed FR / governance markers pending         |
| hub                    | 5     | `HUB-*` markers pending                       |
| config-ts              | 3     | `CONF-*` markers pending                      |
| vessel                 | 3     | `VES-*` markers pending                       |
| governance             | 2     | `GOV-*` markers pending                       |
| forge                  | 1     | single `FORGE-*` marker                       |
| evaluation             | 1     | single `EVAL-*` marker                        |
| types                  | 1     | single `TYPE-*` marker                        |
| **Total**              | **46**|                                               |

The authoritative list of specific IDs is produced at run time by:

```bash
python3 scripts/traceability-check.py 2>&1 | grep '^WARN: Missing'
```

## Acceptance Criteria

1. Running `python3 scripts/traceability-check.py --strict-annotations`
   from repo root exits `0` with no `WARN: Missing` lines.
2. Each of the 46 IDs above resolves to at least one occurrence of the
   literal FR-ID or an `@trace <ID>` annotation inside a tracked source
   or test file (extensions scanned: `.rs`, `.ts`, `.py`, `.yaml`,
   `.yml`, `.md`).
3. `.github/workflows/traceability-gate.yml` is updated to invoke
   `python scripts/traceability-check.py --strict-annotations` and the
   soft-mode comment is removed in the same PR that closes this FR.
4. No new `@trace` alias is introduced that bypasses the
   `SPEC_MARKERS["FR"]` regex in `scripts/traceability-check.py`.

## Non-Goals

- Refactoring the regex vocabulary in `SPEC_MARKERS`.
- Expanding scanned file extensions.
- Rewriting `traceability.json` schema.

## Related

- Unblocks: #54 (fastmcp CRIT) and sibling infra PRs blocked on the
  traceability gate.
- Introduced by: PR `fix/traceability-soft-fail` (refs #168).
