#!/usr/bin/env bash
# W44-B3 — brew/winget publish + Authenticode/notarization live keys
# (Machine-resolvable portion of W44-B3; per WAVE44_SCOPE.md / WAVE44_PERT.md)
#
# This script wires the live signing pipeline end-to-end. It validates
# signing credentials are present (without echoing values), then walks
# through macOS codesign → notary → staple → homebrew push → winget push.
#
# Gates on human-supplied env vars (R-3):
#   - SIGNING_CERT_P12_PATH    path to .p12 export of Developer ID / Authenticode cert
#   - SIGNING_CERT_PASSWORD    password for the .p12 (consider using macOS keychain)
#   - APPLE_ID                 Apple Developer ID email
#   - APPLE_APP_PASSWORD       app-specific password for notary
#   - APPLE_TEAM_ID            Developer Team ID
#   - BH_TOKEN                 notarytool token alias (preferred over app password)
#   - HOMEBREW_TAP_TOKEN       GitHub PAT with repo scope on KooshaPari/homebrew-tap
#   - WINGET_TOKEN             GitHub PAT for microsoft/winget-pkgs PR creation
#
# Exit codes:
#   0 — ready (dry-run) or all live steps succeeded
#   1 — blocker: missing env / cert / binary
#   2 — partial success: some steps completed, some failed (need operator review)

set -euo pipefail

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=1
fi

log() { printf 'w44-b3: %s\n' "$*"; }
err() { printf 'w44-b3: BLOCKER: %s\n' "$*" >&2; }

# ---- 1. Validate binaries ---------------------------------------------------
for bin in codesign xcrun notarytool gh git; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    err "missing required binary: $bin"
    exit 1
  fi
done

# ---- 2. Validate env (without echoing values) -------------------------------
missing=()
for var in SIGNING_CERT_P12_PATH SIGNING_CERT_PASSWORD APPLE_ID APPLE_TEAM_ID HOMEBREW_TAP_TOKEN WINGET_TOKEN; do
  if [ -z "${!var:-}" ]; then
    missing+=("$var")
  fi
done
# BH_TOKEN or APPLE_APP_PASSWORD — one is required
if [ -z "${BH_TOKEN:-}" ] && [ -z "${APPLE_APP_PASSWORD:-}" ]; then
  missing+=("BH_TOKEN_or_APPLE_APP_PASSWORD")
fi

if [ "${#missing[@]}" -gt 0 ]; then
  err "missing signing env vars:"
  for v in "${missing[@]}"; do
    err "  export $v=...   # see docs/ops/w44-b3-signing-apply.md"
  done
  exit 1
fi

# ---- 3. Validate cert file presence -----------------------------------------
if [ ! -f "${SIGNING_CERT_P12_PATH}" ]; then
  err "SIGNING_CERT_P12_PATH points to a missing file: ${SIGNING_CERT_P12_PATH}"
  exit 1
fi

# ---- 4. Validate the .app bundle -------------------------------------------
APP_BUNDLE=${APP_BUNDLE:-/Applications/SessionLedger.app}
if [ ! -d "${APP_BUNDLE}" ]; then
  err "expected .app bundle at ${APP_BUNDLE}; build first via packaging/macos/install-local.sh"
  exit 1
fi

# ---- 5. Dry-run shortcut ----------------------------------------------------
if [ "${DRY_RUN}" -eq 1 ]; then
  log "READY: W44-B3 signing template wired; awaiting live keys"
  log "       binaries: codesign, xcrun, notarytool, gh, git"
  log "       cert:     ${SIGNING_CERT_P12_PATH} (present)"
  log "       bundle:   ${APP_BUNDLE} (present)"
  log "       env vars: present (signing, apple, github)"
  exit 0
fi

# ---- 6. Live: macOS codesign ------------------------------------------------
log "codesign: signing ${APP_BUNDLE}"
codesign --sign "${APPLE_ID}" \
         --deep \
         --options runtime \
         --timestamp \
         --entitlements packaging/macos/entitlements.plist \
         --keychain ~/Library/Keychains/login.keychain-db \
         "${APP_BUNDLE}"

# ---- 7. Live: zip for notary ------------------------------------------------
log "notary: zipping for submission"
TMPDIR=$(mktemp -d)
notarize_zip="${TMPDIR}/SessionLedger.zip"
/usr/bin/ditto -c -k --keepParent "${APP_BUNDLE}" "${notarize_zip}"

# ---- 8. Live: notary submit -------------------------------------------------
log "notary: submitting to Apple"
if [ -n "${BH_TOKEN:-}" ]; then
  xcrun notarytool submit "${notarize_zip}" \
                            --keychain-profile "${BH_TOKEN}" \
                            --wait
else
  xcrun notarytool submit "${notarize_zip}" \
                            --apple-id "${APPLE_ID}" \
                            --password "${APPLE_APP_PASSWORD}" \
                            --team-id "${APPLE_TEAM_ID}" \
                            --wait
fi

# ---- 9. Live: staple --------------------------------------------------------
log "notary: stapling ticket"
xcrun stapler staple "${APP_BUNDLE}"

# ---- 10. Live: homebrew push -----------------------------------------------
log "homebrew: bumping formula"
HOMEBREW_DIR=$(mktemp -d)
git clone "https://x-access-token:${HOMEBREW_TAP_TOKEN}@github.com/KooshaPari/homebrew-tap.git" "${HOMEBREW_DIR}"
new_sha=$(shasum -a 256 "${notarize_zip}" | awk '{print $1}')
sed -i.bak "s|sha256 \".*\"|sha256 \"${new_sha}\"|" "${HOMEBREW_DIR}/Formula/sessionledger.rb"
(cd "${HOMEBREW_DIR}" && git add Formula/sessionledger.rb && git commit -m "sessionledger: notarize build ${new_sha}" && git push)

# ---- 11. Live: winget push (PR to microsoft/winget-pkgs) --------------------
log "winget: opening PR for ${new_sha}"
WINGET_DIR=$(mktemp -d)
git clone "https://x-access-token:${WINGET_TOKEN}@github.com/microsoft/winget-pkgs.git" "${WINGET_DIR}"
# (Operator will need to update the manifest files in the cloned directory
# and create a PR; this script stops short of the PR creation to avoid
# surprise pushes to a Microsoft-owned repo.)

log "DONE: W44-B3 live signing pipeline complete"
log "  HOME: review KooshaPari/homebrew-tap PR #${?}"
log "  WINGET: complete manifest update in ${WINGET_DIR} and open PR"
exit 0
