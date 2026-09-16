# PhenoSpecs migration justification — 2026-09-09

**Decision**: `CONTENT_MIGRATED` — `PhenoSpecs/registry.yaml` migrated into `phenotype-registry`.

**Operator decision**: 2026-09-09, executed by agent11.

## Prior state (reverse chronology)

| Date | Entry | Disposition |
|---|---|---|
| 2026-09-09 | `CONTENT_MIGRATED` | This entry. Operator override. |
| 2026-07-26 | `KEEP_CANONICAL` | PhenoSpecs stays the spec home; phenotype-registry links to it. |
| 2026-06-26 | `pending` → `absorbed_into: registry+papers` | "stale_or_unsupported" (lacked parity proof; repo remained public, active, and the ADRs/contracts home). |
| 2026-06-25 | archive mark | Original archive audit before the prior decision was reversed. |

## Why override

The 2026-07-26 audit concluded KEEP_CANONICAL because PhenoSpecs was the only stable public repo with that role. Operator decision 2026-09-09 *tombstones* PhenoSpecs (rename to `zz-no-archive-PhenoSpecs`, main branch becomes README-only). Once the source repo is tombstoned, the content home role must consolidate elsewhere to keep consumers pointed at a live repo.

## What was migrated

- Source: `KooshaPari/zz-no-archive-PhenoSpecs` `hist` branch, file `registry.yaml`
- Content: 366-line spec↔impl traceability index (3 sections: spec entries, ADR entries, integrations)
- Destination: `phenotype-registry/registry/specs/from-PhenoSpecs/registry.yaml`
- History preserved: `KooshaPari/zz-no-archive-PhenoSpecs` `hist` branch keeps the full git history (223 commits)

## Consumer migration plan

Consumers (repos that referenced `KooshaPari/PhenoSpecs/registry.yaml`):
- Update references to `phenotype-registry/registry/specs/from-PhenoSpecs/registry.yaml`
- Track this migration in `phenotype-registry/registry/registry-deferred.md` until all consumers migrate

## Agent11 evidence

- `/Users/kooshapari/Downloads/chat1-portfolio-audit-2026-09-05/agent11-evidence/phenospecs-registry-tracera-reference-fix.md`
- `/Users/kooshapari/Downloads/chat1-portfolio-audit-2026-09-05/agent11-evidence/directive-A-pre-existing-ci-triage.md`
- `/Users/kooshapari/Downloads/chat1-portfolio-audit-2026-09-05/agent11-evidence/directive-A-followup-pins.md`
- `/Users/kooshapari/Downloads/chat1-portfolio-audit-2026-09-05/agent11-evidence/directive-A-followup-pins-2.md`
- `/Users/kooshapari/Downloads/chat1-portfolio-audit-2026-09-05/agent11-evidence/portfolio-ledger-reconciliation.md`
