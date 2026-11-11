# Retrieval and enrichment pipeline

ResearchLedger treats an imported item as a durable research seed, not the final answer.
Every seed is normalized, fingerprinted, linked to its source, and eligible for bounded
enrichment.

The Markdown interchange target is [Open Knowledge Format (OKF) v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md): each concept has parseable frontmatter with a non-empty `type`, portable links, and a `# Citations` section where claims depend on external sources. OKF intentionally does not prescribe a database or vector engine, so those remain implementation details of the local-first vault.

## Deterministic stages

Stages 1-6 are implemented in the current desktop build. Stages 7-8 remain release gates;
the scorecard must not treat them as shipped.

1. Capture the source payload and immutable provenance.
2. Normalize Markdown, canonical URLs, titles, and timestamps.
3. Extract outbound references into `document_links`, deduplicated by canonical URL.
4. Implemented: schedule bounded reference fetches with robots/private-host/redirect checks,
   a 1 MB body cap, a 15 second timeout, and resumable artifact metadata.
5. Implemented: promote fetched sources to Markdown and distill claims, definitions,
   alternatives, and open questions with source citations.
6. Implemented: index heading/size-bounded chunks in FTS5 and optional vector storage with
   model/version/input-hash metadata.
7. [Partial] Retrieve with reciprocal-rank fusion across lexical and vector results. An opt-in,
   loopback-only cross-encoder adapter is MLX-first on macOS, with TEI and ONNX wire-compatible
   engines for Linux and Windows; deterministic overlap ranking remains the offline fallback.
   The adapter and quality fixture are covered, but an installed-model smoke remains a release
   gate.
8. [Partial] Build answer context with stable citation IDs, source URLs, and capture
   timestamps; confidence/coverage metadata is pending.

## Storage choices

SQLite/Markdown is the default local source of truth. SQLite FTS5 provides deterministic
offline BM25-style retrieval and survives rebuilds from Markdown. A vector adapter should
be selected by corpus size and deployment target:

- SQLite vector extension for a single-user desktop corpus;
- LanceDB for a file-backed local vector index;
- Qdrant for a separately hosted service;
- pgvector only when a server database is already justified.

Dragonfly is an optional hot cache, not canonical storage. NATS is an optional durable
enrichment event bus for multi-process or remote workers. Neo4j is an optional graph query
projection; `document_links` remains sufficient for the local default. MinIO is an optional
object store for large raw captures and media, never a prerequisite for the desktop vault.

Model providers are interfaces, not hardcoded dependencies: local embedding/rerank models
are preferred for privacy, while Gemini or another hosted provider can be explicitly enabled
for higher-quality enrichment. Every model call records provider, model, prompt/version,
input fingerprint, output fingerprint, and citation references.

The first local provider is Ollama’s `/api/embed` endpoint, defaulting to `embeddinggemma`
and configurable to another installed embedding model. Embeddings are opt-in and persisted
per chunk in SQLite; if Ollama is unavailable, lexical FTS5 and deterministic distillation
continue to work without network or model dependencies.

## Local cross-encoder contract

ResearchLedger does not download a reranking model and does not add an in-process ML runtime.
It sends only to an explicitly configured loopback endpoint, so a vault works entirely offline
until the operator has installed and started a local cross-encoder service.

The preferred macOS engine is an MLX-native cross-encoder service that exposes the
Cohere/Jina-style `POST /v1/rerank` contract. MLX LM's official HTTP server is for generative
models, not a cross-encoder rerank endpoint, so it is deliberately not used here. Configure an
already-installed MLX rerank service as follows:

```sh
export RESEARCHLEDGER_RERANK_ENGINE=mlx
export RESEARCHLEDGER_RERANK_ENDPOINT=http://127.0.0.1:9000/v1/rerank
export RESEARCHLEDGER_RERANK_MODEL=local-cross-encoder
```

For Linux, use Hugging Face Text Embeddings Inference (TEI) with a local `/rerank` endpoint;
for Windows, use a local ONNX Runtime DirectML/CPU server that presents the same TEI rerank
contract. Both use `{"query", "texts", "raw_scores": false, "truncate": true}` and return
indexed scores. The configuration is identical except for the engine and endpoint:

```sh
# Linux: local TEI service
export RESEARCHLEDGER_RERANK_ENGINE=tei
export RESEARCHLEDGER_RERANK_ENDPOINT=http://127.0.0.1:8080/rerank
export RESEARCHLEDGER_RERANK_MODEL=BAAI/bge-reranker-large

# Windows: local ONNX Runtime service implementing the TEI rerank shape
export RESEARCHLEDGER_RERANK_ENGINE=onnx
export RESEARCHLEDGER_RERANK_ENDPOINT=http://127.0.0.1:8080/rerank
export RESEARCHLEDGER_RERANK_MODEL=BAAI/bge-reranker-large
```

Without `RESEARCHLEDGER_RERANK_ENGINE`, ResearchLedger selects `mlx` on macOS, `tei` on Linux,
and `onnx` on Windows. The adapter accepts only `http` numeric loopback endpoints
(`127.0.0.0/8` or `::1`), disables proxy routing and redirects, times out after three seconds,
validates every returned candidate index
and finite score, and falls back to deterministic ranking if the service is unavailable or
malformed. The versioned contract fixture at
`apps/desktop/src-tauri/tests/fixtures/retrieval/cross_encoder_contract.json` locks MLX and TEI
semantic ordering independently of a downloaded model artifact.

For release verification, run:

```sh
bun run smoke:rerank
```

The script emits deterministic evidence (`engine`, `endpoint`, `model`, `request_hash`,
`response_hash`, and result order). With no explicit endpoint configuration, it falls back to a
deterministic local ranking report when the fixture candidates are only unavailable (404,
unreachable, or timeout). Set an explicit local reranker endpoint (for example via
`RESEARCHLEDGER_RERANK_ENDPOINT`) to keep this command strict when you want hard failures
instead of local fallback.
