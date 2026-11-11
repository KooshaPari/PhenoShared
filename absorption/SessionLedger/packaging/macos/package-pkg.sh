#!/usr/bin/env bash
# Build an unsigned SessionLedger .pkg from SessionLedger.app via productbuild.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_NAME="${APP_NAME:-SessionLedger}"
VERSION="${VERSION:-0.1.0}"
VERSION="${VERSION#v}"
DIST="${DIST:-$ROOT/packaging/dist}"
APP="${APP:-$DIST/${APP_NAME}.app}"
ARCH_LABEL="${ARCH_LABEL:-}"
BUNDLE_ID="${BUNDLE_ID:-com.sessionledger.viewer}"
INSTALL_LOCATION="${INSTALL_LOCATION:-/Applications}"

command -v productbuild >/dev/null ||
  { echo "productbuild is required (Xcode command line tools)." >&2; exit 1; }

if [[ ! -d "$APP" ]]; then
  echo "Missing app bundle at '$APP'. Run packaging/macos/package-app.sh first." >&2
  exit 1
fi

mkdir -p "$DIST"
if [[ -n "$ARCH_LABEL" ]]; then
  OUT="$DIST/${APP_NAME}-${VERSION}-${ARCH_LABEL}.pkg"
else
  OUT="$DIST/${APP_NAME}-${VERSION}.pkg"
fi
rm -f "$OUT"

productbuild \
  --component "$APP" "$INSTALL_LOCATION" \
  --identifier "$BUNDLE_ID.pkg" \
  --version "$VERSION" \
  "$OUT"

echo "macOS PKG (unsigned): $OUT"
