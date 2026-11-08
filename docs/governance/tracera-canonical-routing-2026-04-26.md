# Tracera Canonical Routing - 2026-04-26

## Decision

`Tracera-recovered` is the canonical source checkout for the recovered TracerTM
product. Do not treat the shelf root `Tracera/`, `artifacts/`, or `phench/` as
the canonical TracerTM implementation.

`Tracera/` remains a preserved legacy observability-platform/docs checkpoint until
its unique content is compared and either migrated or explicitly retired.

`phench/` is a separate Python service orchestration/benchmarking product that is
currently attached to the same `<REDACTED>/Tracera.git` branch family. It must be
routed separately and not folded into TracerTM recovery.

## Routing Table

| Path | Routing | Evidence | Next action |
|---|---|---|---|
| `Tracera-recovered/` | Canonical TracerTM source | Has `backend/go.mod`, `frontend/package.json`, root `package.json`, `process-compose.yml`, deployment docs, OpenAPI/proto/schemas, and recent TracerTM commits. | Rename or reclone into canonical `Tracera/` path only after preserving legacy `Tracera/`. |
| `Tracera/` | Preserved legacy observability checkpoint | README describes an observability platform with Tempo, Prometheus, Loki, Grafana, Alloy, and Minio; current checkout is a worktree-style branch showing shelf-wide status noise. | Compare docs/configs against recovered source; migrate unique observability docs if still relevant. |
| `artifacts/` | Tracera-remote shelf/worktree artifact container | Git remote is `<REDACTED>/Tracera.git`; status output mirrors shelf-wide dirt rather than a coherent product tree. | Keep as quarantine artifact until row-level worktree disposition. |
| `phench/` | Separate product, not TracerTM | README describes `Phench`, a Python service orchestration and benchmarking framework; branch remote points to `<REDACTED>/Tracera.git` and has one local ahead commit. | Create separate routing decision or remote; do not merge into TracerTM. |
| `Tracely/` | Separate deprecated tracing repo | Remote is `<REDACTED>/Tracely.git`; current branch is `chore/dead-code-phase1-tracely`. | Keep under Tracely dead-code/sunset lane. |

## Canonical Evidence For `Tracera-recovered`

- `Tracera-recovered/backend/go.mod` module:
  `github.com/KooshaPari/tracertm-backend`
- `Tracera-recovered/package.json` package:
  `tracertm-workspace`
- `Tracera-recovered/frontend/package.json`
- `Tracera-recovered/process-compose.yml`
- `Tracera-recovered/Taskfile.yml`
- `Tracera-recovered/deploy/k8s/README.md`
- `Tracera-recovered/openapi/README.md`
- `Tracera-recovered/proto/README.md`
- `Tracera-recovered/schemas/README.md`
- `Tracera-recovered/.trace/README.md`

Recent recovered commits:

```text
f9123258 chore: add MIT LICENSE and update README
19e9a9ab docs(worklog): bootstrap worklog scaffolding (org-wide gap closure)
8873600b feat(tracera): tracertm.cli stub with all command modules
048a9699 ci: adopt phenotype-tooling workflows (wave-2)
d7d68840 ci: scope legacy broad workflows
```

## Canonicalization Plan

1. Freeze current local paths. Do not delete `Tracera/`, `Tracera-recovered/`,
   `artifacts/`, or `phench/`.
2. Create a fresh clone of `<REDACTED>/Tracera.git` into a temporary path and
   compare it to `Tracera-recovered`.
3. If the fresh clone matches `Tracera-recovered`, promote `Tracera-recovered`
   as the source of truth and replace the shelf `Tracera/` path only through a
   deliberate move/rename plan.
4. If the fresh clone does not match `Tracera-recovered`, preserve
   `Tracera-recovered` as the recovery source until the missing remote commits
   are pushed or a new branch is opened.
5. Extract unique `Tracera/` observability-platform docs into
   `Tracera-recovered/docs/legacy-observability/` only if they are still useful.
6. Route `phench/` to its own repository or flatten it into the appropriate
   Python orchestration home after a separate product decision.

## Guardrails

- Do not claim Tracera is lost; the recovered checkout contains the real
  multi-service implementation.
- Do not treat `Tracera/` as the implementation source until its docs-only
  observability checkpoint is reconciled.
- Do not merge `phench/` into TracerTM merely because its remote points at
  `<REDACTED>/Tracera.git`.
- Do not delete any Tracera-related path until a row-level disposition exists in
  the worktree quarantine ledger.

## SUNSET-011 Status

Decision complete. Implementation remains a follow-up:

- `SUNSET-011A`: fresh clone compare against `Tracera-recovered`.
- `SUNSET-011B`: promote recovered checkout or push missing recovery branch.
- `SUNSET-011C`: route `phench/` to its own repository/product home.
