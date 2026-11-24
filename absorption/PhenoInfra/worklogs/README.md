# Worklogs

Project worklogs capturing research, decisions, architecture, and completion notes.

## Categories

| File | Purpose |
|------|---------|
| ARCHITECTURE.md | ADRs, library extraction, refactoring decisions |
| RESEARCH.md | Analysis, starred repo research, comparative studies |
| GOVERNANCE.md | Policy, evidence, quality gates, org alignment |
| DUPLICATION.md | Cross-project code duplication findings |
| DEPENDENCIES.md | Dependency audits, upgrades, modernization |
| INTEGRATION.md | External integrations, API changes |
| PERFORMANCE.md | Optimization, benchmarking results |

## Session worklogs (`SESSION_*.md`)

Each `/loop` run emits rows into a session worklog file:

- Per-session: `worklogs/SESSION_<session-id>.md` (one per `/loop` invocation)
- Weekly rollup: `worklogs/SESSION_<iso-week>.md` (e.g. `SESSION_2026-W24.md`)

Schema, field rules, and reserved `notes` keys are defined in
[`docs/governance/no-idle-parallelism-policy.md`](../docs/governance/no-idle-parallelism-policy.md)
(ADR 0010). The audit routine reads these files; rows with malformed
`tick_ts`, non-integer `active_count`, or missing `queued_tasks` are
flagged as `parse_error: true` and excluded from the idle-ratio
computation.

## Index

See `../../INDEX.md` for cross-repo worklog index.
