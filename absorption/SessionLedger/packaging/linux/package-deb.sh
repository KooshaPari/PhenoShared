#!/usr/bin/env bash
set -euo pipefail

# Documented scaffold: creates an unsigned, local-test Debian package.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="${VERSION:-0.1.0}"
ARCH="${ARCH:-amd64}"
BINARY="${BINARY:-$ROOT/target/release/sl-viewer}"
DIST="${DIST:-$ROOT/packaging/dist}"
STAGE="$DIST/deb/sessionledger_${VERSION}_${ARCH}"

command -v dpkg-deb >/dev/null ||
  { echo "dpkg-deb is required." >&2; exit 1; }
[[ -x "$BINARY" ]] ||
  { echo "Build sl-viewer --release or set BINARY to an executable." >&2; exit 1; }

rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN" "$STAGE/usr/bin" "$STAGE/usr/share/applications" \
  "$STAGE/usr/share/doc/sessionledger"
install -m 0755 "$BINARY" "$STAGE/usr/bin/sl-viewer"
install -m 0644 "$ROOT/LICENSE-MIT" "$ROOT/LICENSE-APACHE" \
  "$STAGE/usr/share/doc/sessionledger/"

cat >"$STAGE/DEBIAN/control" <<EOF
Package: sessionledger
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: SessionLedger maintainers
Description: Desktop viewer for SessionLedger session bundles
EOF

cat >"$STAGE/usr/share/applications/sessionledger.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=SessionLedger
Comment=View SessionLedger session bundles
Exec=sl-viewer
Categories=Utility;
Terminal=false
EOF

mkdir -p "$DIST"
dpkg-deb --root-owner-group --build "$STAGE" "$DIST/sessionledger_${VERSION}_${ARCH}.deb"
echo "Unsigned Debian package scaffold: $DIST/sessionledger_${VERSION}_${ARCH}.deb"
