#!/usr/bin/env bash
# Build an unsigned SessionLedger.app from a release sl-viewer binary.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_NAME="${APP_NAME:-SessionLedger}"
VERSION="${VERSION:-0.1.0}"
VERSION="${VERSION#v}"
BINARY="${BINARY:-$ROOT/target/release/sl-viewer}"
DIST="${DIST:-$ROOT/packaging/dist}"
BUNDLE_ID="${BUNDLE_ID:-com.sessionledger.viewer}"
ARCH_LABEL="${ARCH_LABEL:-}"

if [[ ! -x "$BINARY" && ! -f "$BINARY" ]]; then
  echo "Build sl-viewer --release or set BINARY to an executable (got: $BINARY)." >&2
  exit 1
fi

mkdir -p "$DIST"
APP="$DIST/${APP_NAME}.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

install -m 0755 "$BINARY" "$APP/Contents/MacOS/$APP_NAME"

# Embed the application icon (CFBundleIconFile) when the canonical iconset is present.
ICON_EMBEDDED=0
ICONSET_DIR="$ROOT/assets/icons/sessionledger.iconset"
if [[ -d "$ICONSET_DIR" ]]; then
  ICONUTIL_BIN="$(command -v iconutil || true)"
  if [[ -n "$ICONUTIL_BIN" ]]; then
    if "$ICONUTIL_BIN" -c icns "$ICONSET_DIR" -o "$APP/Contents/Resources/AppIcon.icns"; then
      ICON_EMBEDDED=1
    else
      echo "WARN: iconutil failed — skipping icon embed" >&2
    fi
  else
    echo "WARN: iconutil not found — skipping icon embed" >&2
  fi
fi

cat >"$APP/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>${APP_NAME}</string>
  <key>CFBundleDisplayName</key>
  <string>${APP_NAME}</string>
  <key>CFBundleExecutable</key>
  <string>${APP_NAME}</string>
  <key>CFBundleIdentifier</key>
  <string>${BUNDLE_ID}</string>
  <key>CFBundleVersion</key>
  <string>${VERSION}</string>
  <key>CFBundleShortVersionString</key>
  <string>${VERSION}</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>LSMinimumSystemVersion</key>
  <string>11.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
  <key>NSPrincipalClass</key>
  <string>NSApplication</string>
  <key>LSUIElement</key>
  <false/>
  <key>NSSupportsAutomaticGraphicsSwitching</key>
  <true/>
  <key>NSHumanReadableCopyright</key>
  <string>Copyright © 2026 SessionLedger. All rights reserved.</string>
</dict>
</plist>
EOF

if [[ "$ICON_EMBEDDED" == "1" ]]; then
  /usr/bin/plutil -replace CFBundleIconFile -string AppIcon "$APP/Contents/Info.plist"
  /usr/bin/plutil -replace CFBundleIconName -string AppIcon "$APP/Contents/Info.plist"
fi

/usr/bin/plutil -lint "$APP/Contents/Info.plist"

# Stamp architecture into a sidecar for CI naming when ARCH_LABEL is set.
if [[ -n "$ARCH_LABEL" ]]; then
  printf '%s\n' "$ARCH_LABEL" >"$APP/Contents/Resources/arch.txt"
fi

echo "macOS app bundle (unsigned): $APP"
