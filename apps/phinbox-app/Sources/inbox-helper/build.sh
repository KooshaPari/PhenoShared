#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
OUTPUT="${PHINBOX_HELPER_OUTPUT:-$REPO_ROOT/target/release/inbox-helper}"
export SDKROOT="${SDKROOT:-/Library/Developer/CommandLineTools/SDKs/MacOSX26.sdk}"
export MACOSX_DEPLOYMENT_TARGET="${MACOSX_DEPLOYMENT_TARGET:-15.0}"
mkdir -p "$(dirname "$OUTPUT")"
swiftc -parse-as-library -sdk "$SDKROOT" -target arm64-apple-macosx15.0 \
    -framework SwiftUI -framework AppKit "$SCRIPT_DIR"/*.swift -o "$OUTPUT"
printf 'Built native helper: %s\n' "$OUTPUT"
