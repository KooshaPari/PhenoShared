# Research findings

- `npm run verify:resources` reports parity for 9 browser-resource declarations, including the
  runtime `linkedin_signin.mjs` script.
- `npm test` passes 73 tests (`scripts/_capture_common.test.mjs` 60 + `src/App.test.tsx` 9 + 4 script tests).
- Rust `cargo test` passes 82 tests total (81 library + 1 OKF contract); only pre-existing dead-code warnings remain.
- Provenance is stored in SQLite and now refreshes on create, update, and unchanged imports.
- The release branch now persists a `reference_fetches` queue and exposes a bounded worker:
  robots-aware public HTTP, private-host rejection, 1 MB body cap, 15 s timeout, atomic raw
  artifacts, and resumable status/hash metadata.
- Deterministic distillation now emits claims, definitions, alternatives, open questions,
  and `[1]` source citations; fetched artifacts are promoted to `reference:*` Markdown
  source documents with provenance.
- Documents are split into bounded heading-aware chunks; embeddings persist model,
  embedding-version, and input-hash metadata, and vector-only RRF hits are retained.
- Retrieval combines FTS5 and optional Ollama vectors. Apple’s
  [MLX examples](https://github.com/ml-explore/mlx-examples) include BERT but the official
  [MLX LM HTTP server](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/SERVER.md) is a
  generative API, not a cross-encoder reranker. The macOS adapter therefore targets a dedicated
  MLX local service using a Cohere/Jina-style `/v1/rerank` contract. On Linux, Hugging Face
  [TEI documents a native `/rerank` endpoint](https://huggingface.co/docs/text-embeddings-inference/en/quick_tour)
  for cross-encoders; Windows uses a local ONNX Runtime service exposing that same TEI shape.
  The adapter is loopback-only, has a three-second timeout and strict response validation, and
  falls back deterministically. The versioned fixture proves both MLX and TEI response shapes
  without a model download.
