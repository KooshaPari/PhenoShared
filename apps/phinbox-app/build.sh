#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROFILE=debug
CARGO_FLAGS=()
if [[ "${1:-}" == --release ]]; then PROFILE=release; CARGO_FLAGS=(--release); fi
export SDKROOT="${SDKROOT:-/Library/Developer/CommandLineTools/SDKs/MacOSX26.sdk}"
export MACOSX_DEPLOYMENT_TARGET="${MACOSX_DEPLOYMENT_TARGET:-15.0}"
export CARGO_BUILD_JOBS=1
cd "$REPO_ROOT"
cargo build -p phinbox --bin phinbox-app --features mcp,tray-native "${CARGO_FLAGS[@]}"
export PHINBOX_BUILD_DIR="$REPO_ROOT/target/$PROFILE"
PHINBOX_HELPER_OUTPUT="$PHINBOX_BUILD_DIR/inbox-helper" "$SCRIPT_DIR/Sources/inbox-helper/build.sh"
"$SCRIPT_DIR/build-app.sh"
