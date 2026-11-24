# Implementation strategy

Keep SQLite/Markdown authoritative. Add enrichment behind a bounded service interface:
canonical URL -> policy check -> fetch/cache -> raw artifact -> structured distillation ->
provenance edges. Keep provider connectors read-only and isolated by persistent profile.

For retrieval, chunk at heading/size boundaries, persist `embedding_model`, `embedding_version`,
and input hash, then fuse BM25/vector candidates before a local reranker. Do not add
Dragonfly, NATS, Neo4j, MinIO, or a hosted vector database until corpus measurements justify
the operational cost.

The reranker remains an explicit local-service boundary: select MLX/Cohere-v1 on macOS, TEI on
Linux, and ONNX/TEI-compatible on Windows. The Rust client owns endpoint policy, timeouts,
request adaptation, result validation, and deterministic fallback; model installation and service
lifecycle remain an operator-controlled, non-secret concern.
