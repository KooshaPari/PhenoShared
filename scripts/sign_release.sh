#!/usr/bin/env bash
# sign_release.sh — Build + cosign-keyless-sign a release tarball + upload to GH Release.
#
# Run this on any machine with: git, cosign (keyless via Sigstore OIDC), gh CLI.
# Works on macOS, Linux, or WSL.  No local keys required.
#
# Usage:
#   bash scripts/sign_release.sh v0.38                  # build + sign + upload
#   TAG=v0.38 bash scripts/sign_release.sh               # same
#   bash scripts/sign_release.sh v0.38 --no-upload       # just build + sign
#
# Requirements:
#   - cosign: brew install cosign (macOS) / https://docs.sigstore.dev/cosign/installation/
#   - gh CLI authenticated: gh auth login
#
# Note on cosign keyless flow:
#   - First-time use requires browser-based OIDC auth (Sigstore Fulcio)
#   - The browser URL + code will print to terminal; complete in 5 minutes
#   - After auth, signing is non-interactive
#
# Scorecard impact: Signed-Releases check (-1/10) → 10/10 once a GitHub Release
#                   has the tarball + .sig + .cert attached.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAG="${1:-${TAG:-v0.37}}"
GITHUB_REPO="${GITHUB_REPO:-KooshaPari/pheno-harness}"
UPLOAD=1

# Parse flags
for arg in "$@"; do
    case "$arg" in
        --no-upload) UPLOAD=0 ;;
    esac
done

# Helpers
log()  { printf '\033[1;34m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*"; }
fail() { printf '\033[1;31m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*" >&2; exit 1; }

command -v cosign >/dev/null 2>&1 || fail "cosign not installed. Install: brew install cosign"
command -v gh >/dev/null 2>&1 || fail "gh CLI not installed. Install: brew install gh"
command -v git >/dev/null 2>&1 || fail "git not installed"

cd "$REPO_ROOT"

ARTIFACT_NAME="pheno-harness-${TAG}"
TARBALL="${REPO_ROOT}/${ARTIFACT_NAME}.tar.gz"

# === STEP 1: Create release tarball ===
log "Step 1/4: Create tarball ${ARTIFACT_NAME}.tar.gz"

python3 - <<PYEOF
import tarfile, os
OUT = "${TARBALL}"
EXCLUDE = [
    "/.git/", "/.venv/", "/__pycache__/", "/.pytest_cache/",
    "/.ruff_cache/", "/.mypy_cache/", "/htmlcov/",
    "/dist/", "/eval/results/", "/logs/", "/.zig-cache/",
    "/zig-out/", "/rust/target/", "/state/wheels/",
    "/.sandbox/", "/.coverage", "qwen3_5_kernel",
    "${ARTIFACT_NAME}.tar.gz",
]
EXCLUDE_EXTS = {".pyc", ".tmp", ".egg-info", ".coverage", ".air"}
PRUNE = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache",
         ".ruff_cache", ".mypy_cache", "htmlcov", "dist",
         ".zig-cache", "zig-out", ".sandbox", ".coverage"}
# NOTE: eval/, state/, rust/, logs/ are NOT pruned wholesale —
# they contain code + config the consumer needs. Only sub-paths
# matching EXCLUDE below are skipped.
count = 0
size = 0
with tarfile.open(OUT, "w:gz") as tf:
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in PRUNE]
        for f in files:
            fp = os.path.join(root, f).replace("\\\\", "/").lstrip("./")
            ext = os.path.splitext(f)[1]
            if ext in EXCLUDE_EXTS: continue
            if any(ex in "/" + fp for ex in EXCLUDE): continue
            try:
                tf.add(fp)
                count += 1
                size += os.path.getsize(fp)
            except Exception as e:
                print(f"skip {fp}: {e}")
print(f"{count} files, {size//1024} KB uncompressed, tarball {os.path.getsize(OUT)//1024} KB")
PYEOF

# === STEP 2: cosign keyless sign ===
log "Step 2/4: cosign keyless sign (Sigstore OIDC)"

cosign sign-blob "${TARBALL}" \
    --output-signature "${TARBALL}.sig" \
    --output-certificate "${TARBALL}.cert" \
    --yes

log "  Verify:"
cosign verify-blob "${TARBALL}" \
    --signature "${TARBALL}.sig" \
    --certificate "${TARBALL}.cert" \
    --insecure-ignore-tlog || true

# === STEP 3: SHA256 ===
log "Step 3/4: SHA256"
sha256sum "${TARBALL}" > "${TARBALL}.sha256"
cat "${TARBALL}.sha256"

# === STEP 4: Upload to GitHub Release ===
if [[ $UPLOAD -eq 1 ]]; then
    log "Step 4/4: Upload to GitHub Release ${TAG}"
    if ! gh release view "${TAG}" --repo "${GITHUB_REPO}" >/dev/null 2>&1; then
        log "  Release ${TAG} does not exist. Creating..."
        gh release create "${TAG}" \
            --repo "${GITHUB_REPO}" \
            --title "${TAG}-pheno-harness-summit" \
            --generate-notes \
            --prerelease=false
    fi
    gh release upload "${TAG}" \
        "${TARBALL}" \
        "${TARBALL}.sig" \
        "${TARBALL}.cert" \
        "${TARBALL}.sha256" \
        --repo "${GITHUB_REPO}" \
        --clobber
    log "  Uploaded."
else
    log "Step 4/4: SKIPPED (--no-upload). Files:"
    ls -lh "${TARBALL}"*
fi

log "DONE."
echo
log "Files produced:"
ls -lh "${TARBALL}"*
echo
log "Next:"
log "  1. Verify on another machine: cosign verify-blob ${TARBALL} --signature ${TARBALL}.sig --certificate ${TARBALL}.cert"
log "  2. View release: https://github.com/${GITHUB_REPO}/releases/tag/${TAG}"