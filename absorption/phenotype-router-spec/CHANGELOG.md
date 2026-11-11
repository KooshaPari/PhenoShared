# Changelog

All notable changes to the phenotype-router-spec protocol are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- `RouterSchema.v0.2.0` — add `RouterRouting.decision_id` field for cross-system correlation
- `RouterArtifact.evidence_chain` — W3C VC-compatible provenance links for tool invocations
- WebSocket transport binding (current spec is HTTP+JSON+SSE only)
- gRPC transport binding with protobuf schema siblings

## [0.1.0] - 2026-06-24

### Added
- Initial spec published from `plans/2026-06-22-phenotype-ecosystem-router-architecture-v1.md`
- `RouterDispatch` (router-dispatch.json) — task submission + dispatch envelope
- `RouterMailbox` (router-mailbox.json) — engine event streaming
- `RouterTrace` (router-trace.json) — task lifecycle trace events (17 event types)
- `RouterArtifact` (router-artifact.json) — tool call + content extraction results
- `docs/dispatch.md` — dispatch endpoint contracts
- `docs/mailbox.md` — mailbox semantics + event ordering guarantees
- `docs/trace.md` — trace event semantics + OTLP mapping
- `docs/lanes.md` — sync / fanout / tree lane contracts
- Reference implementation pointers: substrate::engine-agentapi, substrate::omniroute-adapter, substrate::cliproxy-adapter, substrate::substrate-trace, substrate::a2a
- License: MIT
