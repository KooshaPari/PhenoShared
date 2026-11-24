# Research: AgilePlus Control-Plane Finish

## Evidence inspected

| Area | Current evidence | Consequence |
|---|---|---|
| Runtime | `process-compose.yml` launches an absent `./target/release/agileplus-api` at HTTP 3000 while Python MCP defaults to gRPC `localhost:50051`. | A declared platform can be healthy only when both actual binaries and resolved HTTP/gRPC endpoints agree. |
| Port contract | `crates/agileplus-domain/src/config/loader.rs` accepts four overlapping port variables; `crates/agileplus-subcmds/src/platform/health.rs` hard-codes API 3000 and MinIO 9000. | Environment precedence and every consumer must be consolidated behind one resolver. |
| Build/API | `crates/agileplus-proto/build.rs` deliberately selects hand-written stubs without `protoc`; generated Python service bases return `UNIMPLEMENTED`. | A successful check is not runtime proof; release build must fail if generated runtime server code is unavailable. |
| Credentials | `crates/agileplus-domain/src/credentials/{file,keychain,factory,store}.rs` contains multiple persistence paths. | Production must forbid plaintext secrets and API keys; keychain and an encrypted portable fallback need explicit selection and proof. |
| Events | Python MCP exposes `stream_agent_events`, while proto and generated service implementation are not proven live. | Streaming requires durable sequence/cursor semantics and a live server-to-MCP integration test. |
| Artifacts | Compose config declares MinIO and health probes, but a deployment declaration alone does not prove artifact put/get, content addressing, or provenance linkage. | Artifact gate requires an object-store round trip plus event/evidence references. |
| Consumers | Tracera can be the first connected consumer after endpoint/auth gates. Grapheon has unresolved merge markers and is not a safe dogfood target. | Consumer ordering is Tracera first, Grapheon only after recovery verification. |

## Source anchors

- `process-compose.yml`: NATS, Dragonfly, Neo4j, MinIO, API, and MCP process claims.
- `crates/agileplus-subcmds/src/platform/health.rs`: actual direct dependency probes.
- `crates/agileplus-domain/src/config/loader.rs`: competing API/gRPC environment overrides.
- `python/src/agileplus_mcp/server.py` and `grpc_client.py`: MCP gRPC address and connection surface.
- `python/src/agileplus_mcp/tools/status.py`: intended streaming tool contract.
- `crates/agileplus-proto/{build.rs,src/stubs.rs}` and generated Python gRPC modules: stub fallback evidence.

## Working assumptions to validate

1. Local development may use explicit non-production development credentials, but no
   profile may write plaintext secret or API-key bytes to files, logs, database rows,
   events, or test fixtures. A portable store must use AES-256-GCM with an Argon2id
   derived key and fail closed when decryption material is unavailable or invalid.
2. Neo4j remains optional only if its absence is represented as degraded and no required
   graph-dependent consumer command claims success.
3. Dogfood evidence is retained outside ephemeral process logs and contains no secrets.
