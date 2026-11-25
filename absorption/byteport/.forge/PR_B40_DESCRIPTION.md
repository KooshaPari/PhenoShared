## Summary
Add Tier-2 coverage gate that enforces code coverage thresholds across BytePort's three tiers: Rust lib ≥71%, Go framework ≥70%, and service/E2E ≥60%.

## Context
This is part of epic_B (Cross-repo consolidation & L1 grading), implementing gate B40. Tier-2 establishes automated quality enforcement at the coverage level, ensuring that each layer of the BytePort stack meets minimum coverage before PRs can merge. This builds on Tier-0 (build/lint gates) and Tier-1 (security/SBOM gates) already in place.

## Changes
- **New workflow** `.github/workflows/tier2-coverage-gate.yml` with four jobs:
  - `rust-lib-coverage` — runs `cargo llvm-cov --lib` on `byteport-transport` with `--fail-under-lines 71`
  - `go-framework-coverage` — runs `go test -coverprofile` on `backend/byteport` with awk-based threshold check at 70%
  - `service-coverage` — runs `npx vitest run --coverage` on `frontend/web` with threshold check at 60%
  - `coverage-summary` — aggregates results and posts a status comment on PRs
- **Updated Taskfile.yml** with four new tasks (`coverage-rust-lib`, `coverage-go`, `coverage-service`, `coverage-gate`) that mirror the CI workflow for local development
- Coverage artifacts are uploaded for each layer with 30-day retention

## Testing
```bash
# Rust lib coverage (local)
cargo llvm-cov --package byteport-transport --lib --fail-under-lines 71

# Go framework coverage (local)
cd backend/byteport && go test -coverprofile=coverage.out -covermode=atomic ./...

# Service/E2E coverage (local)
cd frontend/web && npx vitest run --coverage

# Run all gates at once (local)
task coverage-gate
```

The workflow triggers automatically on every PR to `main`/`master`.

## Links
- Epic: epic_B — Cross-repo consolidation & L1 grading
- Gate: B40 — Tier-2 coverage gate
- Area: compute-infra
