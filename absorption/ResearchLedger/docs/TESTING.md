# Testing

Frontend checks:

```bash
bun run test
bun run build
```

Rust checks:

```bash
CARGO_TARGET_DIR=/tmp/researchledger-target cargo test --manifest-path apps/desktop/src-tauri/Cargo.toml
cargo fmt --manifest-path apps/desktop/src-tauri/Cargo.toml -- --check
```

The current test suite covers the React shell, SQLite vault initialization and idempotent
upserts, FTS5 search, citation-preserving retrieval context, GitHub README decoding, safe
Markdown path handling, and duplicate LinkedIn activity URLs. Network
connectors require fixture-backed contract tests before release; live credentials are never
used in CI.
