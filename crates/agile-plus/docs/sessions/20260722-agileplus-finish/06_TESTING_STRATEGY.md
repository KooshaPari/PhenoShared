# Testing and Auditable Validation Strategy

## Layered gates

| Gate | Command or method | Pass condition |
|---|---|---|
| Build | `cargo build --release`, `cargo test --workspace`, `cargo clippy --all`, `cargo fmt --all --check`, `ruff check python/` | Build includes a real server surface; all configured checks pass. |
| Runtime | Isolated `process-compose` start then `agileplus platform status` | API, NATS, Dragonfly, Neo4j policy, and MinIO report actual status and resolved endpoints. |
| API/gRPC/MCP | Live health request, authenticated gRPC read, MCP initialization and lifecycle command | Each crosses process boundaries and returns project-scoped data. |
| Credentials and API keys | Keychain integration harness, encrypted-fallback harness, and repository secret scan | Neither secret nor API key appears in file/database/event/log/evidence output; AES-256-GCM/Argon2id round trip succeeds; missing material, invalid tag, malformed ciphertext, and weak permissions fail closed and are audited. |
| Events | Restart test plus filtered query/page/cursor and audit-chain tests | Stable ordering, no loss/duplicate, correct scope/type filters. |
| Artifacts | Isolated MinIO put/get/tamper/authorization/failure harness | Verified digest and provenance event; inaccessible or unavailable store fails closed. |
| Streaming | Disconnect/reconnect live API and MCP test | Cursor resumes exactly once, heartbeat works, cross-project access is rejected. |
| Dogfood | Evidence-manifest verifier for each project | Every mandatory reference resolves, hashes verify, scope matches, audit chain validates, and no secret-like value is present. |

## Required consumer test fixture

For Tracera and every later project, create a unique project ID and feature slug. Execute:

1. `specify` with an accepted requirement.
2. `plan` that creates work packages.
3. `implement` against a controlled change.
4. `validate` with the project test command captured as an artifact.
5. `ship` only after the governance gate is recorded.

Capture API/MCP requests and redacted responses, event query pages, stream reconnect output,
artifact metadata/digest, trace/usage IDs, governance decision, and audit verifier result in
the evidence manifest. Grapheon has an additional precondition: `rg -n '^(<<<<<<<|=======|>>>>>>>)'`
returns no matches and its recovered head passes its native build/test gate.

## Completion rule

A rollout is passable only when all gates pass against the current live deployment and the
manifest verifier exits successfully. Unit tests, mock clients, and manually written
summaries are supporting evidence only.
