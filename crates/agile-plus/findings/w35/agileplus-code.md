# AgilePlus Code Gap Report — w35

_Generated: 2026-06-15_

## Summary

AgilePlus is substantially scaffolded with 20+ crates. Core domain + SQLite adapter are implemented and tested (100+ unit tests). API routes are implemented. gRPC stubs exist but may not be fully connected.

## Domain (agileplus-domain)

✅ 100+ tests pass: cycle, feature, work_package, module, metric, sync_mapping, governance, audit, config, credentials, error, ports

## API (agileplus-api)

Routes implemented in crates/agileplus-api/src/routes/:
- audit, backlog, branch, cycle, events, features, governance, import, module, stream, work_packages, worktree

No `todo!` or `unimplemented!` stubs found.

## SQLite (agileplus-sqlite)

Full adapter implementation with migrations.

## gRPC (agileplus-grpc)

Files present: server/{bootstrap,commands,core,features,governance,integrations}.rs

**Gaps (need investigation):**
- P1: CI fails on `Domain Zero-Dep Lint` — domain crate may have introduced a framework dep
- P1: `Buf Lint & Breaking` fails — proto file may have breaking changes
- P1: `Autograder Gate 1` — agileplus-cache fails to load due to workspace dep inheritance issue (agileplus-validate)
- P2: agileplus-refinery + agileplus-triage have unused deps (machete flagged, ignored now)
- P2: No integration tests between API and SQLite adapter
- P2: antipattern-detect: .expect() calls in non-test code (agileplus-artifacts/store.rs:134, agileplus-governance/audit.rs:722)

## CI Status (after latest fixes)

Fixes pushed (dc9eadb1):
- ✅ workspace-audit path parsing bug
- ✅ phenoShared sparse-checkout in CI
- ✅ agileplus-validate + toml added to workspace.dependencies
- ✅ TruffleHog --fail dup fixed
- ✅ cargo-deny stale SHA fixed
- ✅ machete ignore lists fixed
- ✅ eco-029 spec scaffolded for spec-first gate
- ✅ PR body updated with spec reference

Remaining failures (pre-fix, will re-run):
- Snyk — needs API key rotation (external)
- SonarCloud — user-scope token (known non-blocking)
- Domain Zero-Dep Lint — investigating
- Buf Lint — proto changes
