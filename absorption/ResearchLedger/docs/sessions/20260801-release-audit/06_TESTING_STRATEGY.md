# Testing strategy

- Static/resource: `npm run verify:resources`, `npm run build`.
- Frontend/capture: `npm test` (73 tests).
- Rust: `CARGO_TARGET_DIR=/tmp/researchledger-target cargo test --manifest-path apps/desktop/src-tauri/Cargo.toml` (81 tests).
- Retrieval quality: `cross_encoder_contract.json` supplies candidate text, MLX/Cohere-v1 and
  TEI response forms, and expected order. Unit tests prove platform engine selection, wire-shape
  adaptation, strict response validation, loopback-only endpoint policy, and rank application.
  Added deterministic smoke command: `npm run smoke:rerank`. Current evidence shows
  `RERANK_ENDPOINT_ERROR http://127.0.0.1:9000/v1/rerank: HTTP 404 Not Found` (endpoint present,
  contract mismatch path). Gate remains operator-unresolved until a local reranker service is
  available and healthy.
- Release: build app-only bundle, verify packaged resources, install, then smoke provider
  menus and vault/export flows. The current installed executable is SHA-256
  `adf1facbfc860afda22fa9151627c8c81519e4fe42466bb500ea1d566ae95895`; packaged Playwright
  module import and resource parity both pass.
- Account smoke: run LinkedIn capture and GitHub import only with the user's authenticated
  local profile; record counts/hashes, never tokens or raw snapshots.
