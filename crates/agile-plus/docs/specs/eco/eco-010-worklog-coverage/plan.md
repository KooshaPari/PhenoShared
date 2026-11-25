# Plan — eco-010 Worklog Coverage

## Objective

Bring fleet-wide `worklogs/` coverage from 1/156 to 156/156 with a single dated entry per active repo on 2026-06-05.

## Scope

- In: create `worklogs/` in every repo on the gap list; append one dated entry; update the coverage snapshot.
- Out: rewriting existing worklogs, retroactive backfill, content audits.

## Implementation Steps

1. **Consume the gap list** — read `worklogs/worklog-coverage-20260605.json` (155 missing repos) and treat it as the authoritative target set.
2. **Branch per repo** — for each repo, create `chore/worklog-seed-<repo>` from `main`. Skip the branch step and seed via the canonical dir if disk blocks the fan-out; record that deviation in the entry.
3. **Seed the directory** — add `worklogs/2026-06-05-fleet-readiness.md` containing:
   - date header,
   - reason (eco-010 closure),
   - one-line statement that prior entries are absent,
   - pointer to the gap list snapshot.
4. **Update the coverage snapshot** — overwrite the JSON with `covered: 156/156`, `generated_at: 2026-06-05T...Z`, and the per-repo status.
5. **Verify** — re-run the coverage check; ensure AC-1/AC-2/AC-3 pass.

## Dependencies

- Step 1 → Step 2 (sequential).
- Steps 2-3 are embarrassingly parallel across repos.
- Step 4 depends on completion of all per-repo seeds.
- Step 5 depends on Step 4.
