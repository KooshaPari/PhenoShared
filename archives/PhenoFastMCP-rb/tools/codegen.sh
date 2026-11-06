#!/usr/bin/env bash
# Regenerate language bindings from core/mcp-idl/proto/*.proto
#
# Idempotent. Safe to re-run. Run before committing any .proto change.

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
PROTO_DIR="$ROOT/core/mcp-idl/proto"
RUST_DIR="$ROOT/core/mcp-idl/rust"
GO_DIR="$ROOT/core/mcp-idl/go"

echo "=== Regenerating Rust bindings ==="
( cd "$RUST_DIR" && cargo build )

echo "=== Regenerating Go bindings ==="
( cd "$GO_DIR" && \
    [ -d "$PROTO_DIR" ] && \
    protoc --go_out=. --go_opt=paths=source_relative \
        "$PROTO_DIR"/*.proto 2>/dev/null \
    || echo "(protoc not installed; skipping Go codegen)" )

echo "=== Done ==="
echo "Proto changes: $PROTO_DIR"
echo "Rust output:   $RUST_DIR/src/"
echo "Go output:     $GO_DIR/"
