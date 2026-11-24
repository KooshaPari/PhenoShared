# Known Issues and Release Blockers

| Severity | Blocker | Current state | Required resolution |
|---|---|---|---|
| P0 | Clean runnable build | Proto build can select hand-written stubs; generated Python base services are `UNIMPLEMENTED`. | Generated server code and live RPC verification are required before release. |
| P0 | Runtime endpoint contract | API 3000, gRPC 50051, MinIO 9000, and multiple API env names are declared independently; 9000 has previously been occupied by an unrelated process. | One resolver, preflight port ownership, and aligned launcher/probe/client configuration. |
| P0 | Platform services | NATS, Dragonfly, Neo4j, MinIO, API, and MCP have been unavailable during readiness inspection. | Isolated compose start with bounded probes and explicit degraded rules. |
| P0 | Credentials and API keys | File and keychain stores coexist; at-rest encryption and fallback behavior cannot be inferred from intent. | Keychain-first factory, AES-256-GCM/Argon2id fail-closed fallback, and redaction verification. |
| P0 | Event evidence | Current client streaming surface does not prove a persistent server implementation or type query. | Durable repository, live query/stream tests, cursor contract. |
| P0 | Artifact evidence | MinIO compose entry and probe do not prove artifact storage. | Real adapter plus put/get/digest/authorization/provenance tests. |
| P0 | Consumer streaming | MCP tool definitions and mock tests are insufficient for connected consumption. | Live API/MCP stream resume and authorization proof. |
| P0 | Grapheon | Unresolved merge markers make it an unsafe consumer baseline. | Reconcile conflicts, inspect diff, build/test clean head, then dogfood. |

No issue in this table may be waived by a mocked test or documentation assertion.
