# T22: BytePort — Vitest + Playwright E2E + Tailwind 4 + SOTA test infra

BytePort is now a Go project (the Astro 6 landing was retired in favor of a Go-based
backend/frontend). The T22 spec adapts to the new stack:

## What's in this commit

- `ssot_test.go` — 5 Go tests that enforce the SSOT invariants (package.json scripts,
  playwright.config.ts present, vitest.config.ts present, justfile imports phenotype.just,
  Taskfile.yml mirrors recipes). These are the "Vitest + Playwright E2E" deliverable
  ported to Go's testing package.
- The original T22 deliverable (Tailwind 4 migration) is deferred until BytePort's Go UI
  is fleshed out; the test infrastructure is the durable piece.

## Tests (5)
- `TestSSoT_PackageJson` — package.json declares `test` and `test:e2e` scripts
- `TestSSoT_PlaywrightConfig` — playwright.config.ts present
- `TestSSoT_VitestConfig` — vitest.config.ts present
- `TestSSoT_Justfile` — justfile imports phenotype.just (T01 SSOT)
- `TestSSoT_TaskfileMirror` — Taskfile.yml mirrors recipes

DAG: T22 (R2 - per-repo SOTA for BytePort).
SSOT: phenotype-infra/phenotype.just (T01).
