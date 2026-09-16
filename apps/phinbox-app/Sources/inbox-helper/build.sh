#!/usr/bin/env bash
# build.sh - Compile the Phinbox inbox-helper Swift binary
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
OUTPUT_DIR="${REPO_ROOT}/target/release"
OUTPUT="${OUTPUT_DIR}/inbox-helper"

echo "Building inbox-helper..."
echo "  Source: ${SCRIPT_DIR}/*.swift"
echo "  Output: ${OUTPUT}"

mkdir -p "${OUTPUT_DIR}"

swiftc \
    -Onone \
    -parse-as-library \
    -framework Cocoa \
    -framework SwiftUI \
    "${SCRIPT_DIR}/Models.swift" \
    "${SCRIPT_DIR}/InboxManager.swift" \
    "${SCRIPT_DIR}/Brand.swift" \
    "${SCRIPT_DIR}/RootView.swift" \
    "${SCRIPT_DIR}/RowView.swift" \
    "${SCRIPT_DIR}/DetailView.swift" \
    "${SCRIPT_DIR}/main.swift" \
    -o "${OUTPUT}"

chmod +x "${OUTPUT}"

echo "Build succeeded: ${OUTPUT}"
echo "Run with: ${OUTPUT}"
