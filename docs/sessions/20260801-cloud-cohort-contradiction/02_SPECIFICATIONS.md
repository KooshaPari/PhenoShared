# Reconciliation Specification

## Invariants

- Preserve all current remote refs and any locally retained source evidence.
- Do not infer authorization from `archived=true`, a `zz-archive-*` name, a 404, or a redirect.
- Do not update `registry/disposition-index.json` from this packet.
- Do not restore, unarchive, rename, delete, force-push, or rewrite history in this lane.
- A 404 is an unresolved provenance state, not evidence that content was intentionally retired.
- `PriceyApp` remains untouched because it is a fork.

## Classification

| Class | Rows | Safe conclusion | Required next proof |
|---|---|---|---|
| Archive-named target/archived | 11 | Current archive-named path and archived head are observable | GitHub audit actor/time plus sponsor receipt or prior authorization |
| Archived in place | `router-docs`, `template-commons` | Current repository remains addressable and archived | Same actor/authorization receipt; then reconcile boundary docs |
| 404 | recovery evidence, harmonizer archive, `4sgm-archive` | Owner API path unavailable under current credentials | Bundle/redirect/search/audit evidence; do not recreate or delete |
| Active fork | `PriceyApp` | Must remain untouched | None for mutation; preserve current fork metadata |
| Active non-forks | `Quillr`, `Stashly`, `phenotype-teamcomm` | Current active state is observable | Re-check disposition against current refs before any proposal |

## Evidence strength

The snapshot is strong for current repository metadata and default-branch heads. It is weak for
historical transitions because the REST repository response does not include the rename/archive
actor or sponsor authorization. Accordingly, this packet reports contradiction and risk, not an
unauthorized-action finding.
