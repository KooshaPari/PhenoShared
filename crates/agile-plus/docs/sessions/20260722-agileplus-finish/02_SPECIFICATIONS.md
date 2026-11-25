# AgilePlus Finish Specification

## Required control-plane capabilities

### R1 — Resolved runtime contract

Provide one typed runtime configuration object with named HTTP, gRPC, NATS, Dragonfly,
Neo4j, MinIO, database, and profile fields. It must be the only source used by launch,
server bind, MCP client, dashboard, health, and emitted diagnostics. Reject zero,
duplicate, unavailable, malformed, or production-insecure endpoints before startup.
`agileplus platform status` must report the exact resolved endpoints and distinguish
healthy, degraded, and down services.

### R2 — Clean production build and live service surface

Release build must generate protobuf and compile a real API/gRPC server. The build may
not silently select hand-written stub service types for a runnable profile. The launcher
must start the real binaries, wait for bounded readiness, surface child logs, and stop
children reliably. A live API health call, gRPC feature call, and MCP initialization are
mandatory release evidence.

### R3 — Credential protection

Credential and API-key writes and reads use the OS keychain through an explicit
`CredentialStore` implementation when it is available. When the keychain is unavailable,
the only persistent fallback is a file encrypted with AES-256-GCM using a key derived by
Argon2id from supplied secret material and a unique stored salt. The fallback must fail
closed for absent/invalid derivation material, malformed ciphertext, authentication-tag
failure, unsupported version, or unsafe permissions; it may never downgrade to plaintext
or a weaker algorithm. Development-only fixtures use clearly named ephemeral in-memory
stores. Logs, audit events, errors, exports, and diagnostics expose stable credential or
API-key references but never secret values. Rotation, deletion, unavailable-keychain,
fallback decrypt failure, and unauthorized-read outcomes are explicit, audited, and tested.

### R4 — Durable events and query

Every lifecycle, usage, trace, governance, artifact, and credential-reference event has
an immutable ID, timestamp, project, feature, work package, actor, event type, payload
hash, correlation ID, and monotonic per-stream sequence. Persistent storage supports
filtered event-type queries, project/feature/WP scope, ordered pagination, and a
resume cursor. Query and stream return identical ordering semantics.

### R5 — MinIO artifacts

Implement an artifact adapter backed by MinIO/S3 with bucket initialization, content
digest, size, media type, owner scope, creation event, retrieval authorization, and
verified download integrity. Store only artifact metadata/references in the event store;
never embed large artifact bytes or secrets in events. Failure to reach MinIO blocks
artifact-producing workflows rather than reporting success.

### R6 — MCP/API streaming

Expose authenticated streaming for the API and MCP. Both surfaces consume the same
durable event cursor, send a bounded heartbeat, preserve correlation and sequence
fields, reject cross-project subscriptions, and resume without duplicates after a
disconnect. The generated gRPC server must back the MCP client; an in-process mock does
not satisfy this requirement.

## Dogfood specification

Each project rollout creates a project-scoped evidence pack containing a signed manifest,
resolved configuration with secrets redacted, feature/WP identifiers, API/MCP transcript,
event query result, stream resume proof, artifact digest/retrieval proof, trace/usage
records, governance decision, audit-chain verification, test report, and operator
attestation. Retention location, access policy, and immutable manifest digest are recorded.

### Gate order

1. AgilePlus release gates R1-R6 pass in a clean worktree and isolated runtime.
2. Tracera completes `specify -> plan -> implement -> validate -> ship` through API/MCP.
3. Grapheon repository recovery removes every conflict marker, builds/tests from its
   reconciled head, and then repeats the Tracera journey.
4. Each later project repeats the same pack with a fresh project scope; no evidence is
   copied across project IDs.
