#!/usr/bin/env bash
set -euo pipefail

# Documented scaffold: requires appimagetool on PATH and a Linux release binary.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="${VERSION:-0.1.0}"
BINARY="${BINARY:-$ROOT/target/release/sl-viewer}"
DIST="${DIST:-$ROOT/packaging/dist}"
APPDIR="$DIST/SessionLedger.AppDir"

command -v appimagetool >/dev/null ||
  { echo "appimagetool is required (https://appimage.github.io/)" >&2; exit 1; }
[[ -x "$BINARY" ]] ||
  { echo "Build sl-viewer --release or set BINARY to an executable." >&2; exit 1; }

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
install -m 0755 "$BINARY" "$APPDIR/usr/bin/sl-viewer"

cat >"$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/sl-viewer" "$@"
EOF
chmod 0755 "$APPDIR/AppRun"

# appimagetool refuses to build (exit 1) when the desktop entry references an
# icon that is not present in the AppDir. Ship the brand icon so packaging
# succeeds instead of failing silently under continue-on-error.
ICON_SRC="$ROOT/assets/icons/sessionledger.iconset/icon_256x256.png"
if [ -f "$ICON_SRC" ]; then
    install -m 0644 "$ICON_SRC" "$APPDIR/sessionledger.png"
else
    echo "warning: brand icon not found at $ICON_SRC; AppImage will be built without an icon." >&2
fi

cat >"$APPDIR/sessionledger.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=SessionLedger
Comment=View SessionLedger session bundles
Exec=sl-viewer
Icon=sessionledger
Categories=Utility;
Terminal=false
EOF

mkdir -p "$DIST"
ARCH="${ARCH:-x86_64}" appimagetool "$APPDIR" "$DIST/SessionLedger-$VERSION-${ARCH:-x86_64}.AppImage"
echo "Unsigned AppImage scaffold: $DIST/SessionLedger-$VERSION-${ARCH:-x86_64}.AppImage"
