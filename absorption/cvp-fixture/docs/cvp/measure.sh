#!/bin/bash
# CVP Pilot Measurement Script
# Run after each agent completes the pilot task
# Usage: ./measure.sh [label]

set -e
LABEL="${1:-unnamed}"
REPO="$HOME/CodeProjects/cvp-fixture"
cd "$REPO"

echo "=== CVP Pilot Measurement: $LABEL ==="
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# 1. Git status
echo "--- Git Status ---"
git log --oneline -5
echo ""
echo "Files changed from initial commit:"
git diff --stat 9fab276 HEAD 2>/dev/null || echo "(no commits beyond initial)"
echo ""

# 2. Test results
echo "--- Test Results ---"
cargo test 2>&1 | tail -20
echo ""

# 3. Warnings
echo "--- Compiler Warnings ---"
cargo check 2>&1 | grep -c "warning:" || echo "0"
echo ""

# 4. Clippy
echo "--- Clippy ---"
cargo clippy 2>&1 | grep -c "warning" || echo "0"
echo ""

# 5. Doc coverage
echo "--- Public items without doc comments ---"
grep -rn "pub " pipeline/src/ | grep -v "pub(crate)" | grep -v "//" | grep -v "pub fn\|pub struct\|pub trait\|pub enum\|pub type" | head -10
echo ""

# 6. DeduplicateFilter verification
echo "--- DeduplicateFilter Test ---"
cargo test deduplicate 2>&1 | tail -5
echo ""

echo "=== Measurement complete ==="
