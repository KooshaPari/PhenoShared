# T22 — BytePort (formerly byteport-landing) SOTA push

## Scope

The T22 deliverable in the R2 (per-repo SOTA) wave covers the former
`byteport-landing` Astro 6 site. The repo has since been renamed to
`BytePort` and rewritten in Go. T22 enforces the T1 / T2 / T5
governance contracts on the Go rewrite.

## Deliverables

1. **`ports/ssot_test.go`** — Go-native SSOT invariants (103 lines, 5
   tests) that verify:
   - `justfile` imports `phenotype.just` (T01 SSOT)
   - `Taskfile.yml` mirrors the justfile recipes (T1 compat layer)
   - `CODEOWNERS` is present (T05 SSOT)
   - `.gitignore` covers the T19 SSOT categories (node_modules, .env, dist)

2. **This README** — documents the T22 scope and ties it back to the
   100-task DAG.

## DAG traceability

- T22 (R2 - per-repo SOTA push for BytePort/byteport-landing)
- Depends on: T01 (phenotype.just), T05 (CODEOWNERS), T19 (.gitignore)
- Pattern SSOT: `phenoData/ports/query_port.rs` (the hexagonal port pattern)

## Audit results

| Gate | Result |
|------|--------|
| `go test ./ports/...` | PASS (5/5) |
| `just --list` | Lists 30+ recipes (phenotype.just import OK) |
| `task --list` | Lists mirrored recipes (T1 compat) |
| `git check-ignore -v .env dist/ node_modules/` | Exit 0 (T19 coverage) |

## Pre-existing issues (tracked, not in T22 scope)

- `@tailwindcss/vite` version mismatch: see the
  `gh issue list --search "tailwindcss vite"` results; will be fixed in
  T83 (R5 SOTA Bun + Node upgrade) as part of the org-wide JS upgrade.
