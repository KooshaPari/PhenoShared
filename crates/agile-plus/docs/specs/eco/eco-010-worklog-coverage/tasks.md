# Tasks — eco-010 Worklog Coverage

| WP | Title | Depends On | Description |
|----|-------|------------|-------------|
| WP-01 | Load gap list | — | Parse `worklogs/worklog-coverage-20260605.json`; emit 155 missing repo slugs. |
| WP-02 | Seed per-repo worklogs | WP-01 | For each repo, create `worklogs/2026-06-05-fleet-readiness.md` on `chore/worklog-seed-<repo>` (or canonical dir if disk-blocked). |
| WP-03 | Refresh coverage snapshot | WP-02 | Rewrite `worklogs/worklog-coverage-20260605.json` with `covered: 156/156` and per-repo status. |
| WP-04 | Verify acceptance | WP-03 | Re-run coverage check; confirm AC-1 (`156/156`), AC-2 (UTF-8 + date header), AC-3 (no silent skips). |
