#!/usr/bin/env bash
# sign_macos.sh — Sign the pheno-harness macOS kernel + tarball locally.
#
# Run this on a MacBook (or any macOS machine) with the repo checked out.
# Produces two complementary artifacts:
#   1. Apple ad-hoc codesign signature (passes Gatekeeper locally)
#   2. cosign signature + cert (cross-platform verifiable, scorecard-friendly)
#
# Cost: $0/yr. No Apple Developer ID required for ad-hoc signing.
# For distribution outside the App Store with Gatekeeper passing on other
# people's machines, get a Developer ID ($99/yr) and switch ADHOC=0 below.
#
# Usage:
#   bash scripts/sign_macos.sh                 # sign + verify
#   bash scripts/sign_macos.sh --upload        # also upload to GitHub Release
#   ADHOC=0 bash scripts/sign_macos.sh         # use Developer ID instead
#   SIGN_ONLY=qwen3_5_kernel bash scripts/sign_macos.sh
#
# Requirements:
#   - macOS (10.15+) with Xcode Command Line Tools
#   - cosign: brew install cosign
#   - gh CLI (only if --upload): brew install gh

set -euo pipefail

# Config
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KERNEL_DIR="${REPO_ROOT}/kernels/qwen3.5-0.8b"
KERNEL_BIN="${KERNEL_DIR}/pony/qwen3_5_kernel"
ARTIFACT_NAME="pheno-harness-v0.37"
TARBALL="${REPO_ROOT}/${ARTIFACT_NAME}.tar.gz"
GITHUB_REPO="${GITHUB_REPO:-<REDACTED>/pheno-harness}"

# Signing mode: 1 = ad-hoc (free), 0 = Developer ID (requires $99/yr cert)
ADHOC="${ADHOC:-1}"
DEVELOPER_ID="${DEVELOPER_ID:-}"  # e.g. "Developer ID Application: Your Name (TEAMID)"

# Parse flags
UPLOAD=0
for arg in "$@"; do
    case "$arg" in
        --upload) UPLOAD=1 ;;
        --help|-h)
            sed -n '2,30p' "$0"
            exit 0
            ;;
    esac
done

# Helpers
log()  { printf '\033[1;34m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*"; }
warn() { printf '\033[1;33m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
fail() { printf '\033[1;31m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*" >&2; exit 1; }

# Pre-flight
[[ "$(uname)" == "Darwin" ]] || fail "Must run on macOS (got: $(uname))"
[[ -f "$KERNEL_BIN" ]] || fail "Kernel binary not found: $KERNEL_BIN (run bash scripts/build_all.sh in kernels/qwen3.5-0.8b/ first)"
command -v cosign >/dev/null 2>&1 || fail "cosign not installed. Install: brew install cosign"
command -v gh >/dev/null 2>&1 || [[ $UPLOAD -eq 0 ]] || fail "gh CLI required for --upload. Install: brew install gh"

cd "$REPO_ROOT"

# === STEP 1: Apple codesign (ad-hoc or Developer ID) ===
log "Step 1/4: Apple codesign ($([[ $ADHOC -eq 1 ]] && echo "ad-hoc" || echo "Developer ID"))"

ENTITLEMENTS="${KERNEL_DIR}/scripts/entitlements.plist"
if [[ ! -f "$ENTITLEMENTS" ]]; then
    cat > "$ENTITLEMENTS" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.cs.allow-dyld-environment-variables</key>
    <true/>
</dict>
</plist>
EOF
    log "Created ${ENTITLEMENTS}"
fi

if [[ $ADHOC -eq 1 ]]; then
    log "  codesign --force --deep --sign - $KERNEL_BIN"
    codesign --force --deep --sign - --options runtime --entitlements "$ENTITLEMENTS" "$KERNEL_BIN"
else
    [[ -n "$DEVELOPER_ID" ]] || fail "ADHOC=0 requires DEVELOPER_ID=\"Developer ID Application: Name (TEAMID)\""
    log "  codesign --force --deep --sign \"$DEVELOPER_ID\" --timestamp $KERNEL_BIN"
    codesign --force --deep --sign "$DEVELOPER_ID" --options runtime --entitlements "$ENTITLEMENTS" --timestamp "$KERNEL_BIN"
fi

log "  Verify:"
codesign -dv "$KERNEL_BIN" 2>&1 | head -10
echo

# === STEP 2: Create release tarball ===
log "Step 2/4: Create tarball"
log "  tar -czf $TARBALL -C $(dirname $REPO_ROOT) $(basename $REPO_ROOT) --exclude=...'"
# Exclude heavy + generated dirs to keep tarball small
tar -czf "$TARBALL" \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='.ruff_cache' \
    --exclude='.mypy_cache' \
    --exclude='*.egg-info' \
    --exclude='state/wheels' \
    --exclude='.coverage*' \
    --exclude='htmlcov' \
    --exclude='dist' \
    --exclude='*.tmp' \
    --exclude='eval/results' \
    --exclude='logs' \
    --exclude='*.pyc' \
    --exclude='kernels/**/build' \
    --exclude='kernels/**/.zig-cache' \
    --exclude='kernels/**/zig-out' \
    --exclude='kernels/**/rust/target' \
    --exclude='kernels/**/pony/qwen3_5_kernel' \
    -C "$(dirname "$REPO_ROOT")" "$(basename "$REPO_ROOT")"

TARBALL_SIZE=$(du -h "$TARBALL" | cut -f1)
log "  Created: $TARBALL ($TARBALL_SIZE)"

# === STEP 3: cosign keyless signing ===
log "Step 3/4: cosign keyless sign (Sigstore OIDC, no keys needed)"
cosign sign-blob "$TARBALL" \
    --output-signature "$TARBALL.sig" \
    --output-certificate "$TARBALL.cert" \
    --yes

log "  Verify:"
cosign verify-blob "$TARBALL" \
    --signature "$TARBALL.sig" \
    --certificate "$TARBALL.cert" \
    --insecure-ignore-tlog  # keyless requires transparency log lookup, skip for offline verify

echo
log "  Files produced:"
ls -lh "$TARBALL" "$TARBALL.sig" "$TARBALL.cert"

# === STEP 4: SHA256 + optional upload ===
log "Step 4/4: SHA256"
sha256sum "$TARBALL" > "$TARBALL.sha256"
cat "$TARBALL.sha256"

if [[ $UPLOAD -eq 1 ]]; then
    log "  Uploading to GitHub Release v0.37-pheno-harness-summit..."
    gh release upload "v0.37-pheno-harness-summit" \
        "$TARBALL" \
        "$TARBALL.sig" \
        "$TARBALL.cert" \
        "$TARBALL.sha256" \
        --repo "$GITHUB_REPO" \
        --clobber
    log "  Uploaded."
fi

echo
log "DONE."
log "  Apple signature : codesign -dv $KERNEL_BIN"
log "  cosign signature : $TARBALL.sig"
log "  cosign cert     : $TARBALL.cert"
log "  SHA256          : $TARBALL.sha256"

if [[ $ADHOC -eq 1 ]]; then
    echo
    warn "Ad-hoc signing only — Gatekeeper will warn on OTHER Macs."
    warn "  For public distribution, get Apple Developer ID (\$99/yr):"
    warn "  ADHOC=0 DEVELOPER_ID=\"Developer ID Application: Your Name (TEAMID)\" bash scripts/sign_macos.sh"
fi

if [[ $UPLOAD -eq 0 ]]; then
    echo
    log "To upload to GitHub Release v0.37:"
    log "  bash scripts/sign_macos.sh --upload"
fi