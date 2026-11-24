# agileplus (KooshaPari/AgilePlus)

Source: cmd/dagrun/docs/research/agileplus-surface.md and cmd/dagrun/docs/research/agileplus-parity.md (primary: https://github.com/KooshaPari/AgilePlus)

## What it is

AgilePlus is a Rust workspace (canonical owner KooshaPari/AgilePlus) for feature lifecycle, governance, work packages, audit chain, queue, retrospective, and (upstream only) atomic acceptance. Authoritative version: Cargo.toml [workspace.package] version 0.2.4. Peak = main tip 8699676312dfcd787435221a7926a407af920fc6 (2026-11-10T01:59:57Z). Installed binary reports 0.2.4. VERSION file (0.1.2) and CHANGELOG (2026.08A.0) are stale; CalVer and SemVer tags do not order (v2026.09.0 is older than v0.2.4).

## Artifact model

- CLI writes docs/agileplus/<slug>/spec.md (specify), kitty-specs/<slug>/research.md (research), work packages (plan).
- MCP package PhenoShared/python/src/agileplus_mcp exposes 22 @mcp.tool decorators: agileplus_specify, agileplus_research, agileplus_plan, agileplus_status, agileplus_stream_status, agileplus_validate, agileplus_verify_audit_chain, agileplus_check_governance_gate, agileplus_elicit_clarify, agileplus_elicit_feature, agileplus_queue_add/import/list/pop/show, agileplus_implement, agileplus_retrospective, agileplus_sample_governance_check, agileplus_sample_retrospective, agileplus_sample_triage, agileplus_ship.
- Atomic acceptance slice (15 files: domain command + oracle, domain port, application preflight + write path, sqlite transaction + receipt, migration 030, HTTP route, gRPC service + server, 4 test suites) exists only upstream @ 8699676; absent from PhenoShared (zero hits for AcceptFeatureCommand, TerminalAcceptancePort, accept_feature_atomic, feature_acceptance_receipts). Absorbed crates/agile-plus is an older snapshot (migrations to 026 vs upstream 030).

## Traceability enforcement

Atomic acceptance (upstream only) gives requirement -> candidate -> receipt chain with DB-level immutable receipts (feature_acceptance_receipts, no_update/no_delete triggers, request_id PK idempotency). Elsewhere: governance gate, audit chain, feature lifecycle, work packages. CLI callable: specify, research, plan, list, validate, dag, mvp. No accept/verify/freeze verb in installed binary (exact-peak CLI exposure UNKNOWN due to 55 days unreleased commits).

## Interface

CLI (Rust binary) + MCP (Python proxy to gRPC backend on localhost:50051). Deployment status UNKNOWN (fastmcp absent in absorbed tree; no gRPC server binary identified). No SDK documented.

## Interactivity

Multi-turn via MCP elicit_feature / elicit_clarify (already shipped; must not be rebuilt). CLI is one-shot per verb.

## External verification

validate exits 1 on wrong state or missing feature. Atomic acceptance has HTTP/gRPC/sqlite test suites upstream (4 suites). MCP surface deployment UNKNOWN (real tool-loop call required before claiming runnable).

## License

UNKNOWN (not stated in drafts).

## Notes

Canonical AgilePlus for integration is main @ 8699676 (0.2.4), not the absorbed copy or any CalVer tag; atomic acceptance is absent from PhenoShared by snapshot age, not dropped files.
