#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="${PHINBOX_BUILD_DIR:-$REPO_ROOT/target/release}"
APP_NAME="${PHINBOX_APP_NAME:-Phinbox}"
APP_DIR="${PHINBOX_BUNDLE_DIR:-$SCRIPT_DIR/dist/$APP_NAME.app}"
[[ -f "$BUILD_DIR/phinbox-app" && -f "$BUILD_DIR/inbox-helper" ]] || { echo 'Build both Rust host and Swift helper first.' >&2; exit 1; }
mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources"
cp "$BUILD_DIR/phinbox-app" "$APP_DIR/Contents/MacOS/phinbox"
cp "$BUILD_DIR/inbox-helper" "$APP_DIR/Contents/Resources/inbox-helper"
cp "$SCRIPT_DIR/Resources/AppIcon.icns" "$APP_DIR/Contents/Resources/AppIcon.icns"
python3 - "$SCRIPT_DIR/Info.plist" "$APP_DIR/Contents/Info.plist" "$APP_NAME" "${PHINBOX_BUNDLE_ID:-com.phenotype.phinbox}" <<'PY'
import plistlib,sys
with open(sys.argv[1],'rb') as f: p=plistlib.load(f)
p.update(CFBundleName=sys.argv[3],CFBundleDisplayName=sys.argv[3],CFBundleIdentifier=sys.argv[4],LSMinimumSystemVersion='15.0')
with open(sys.argv[2],'wb') as f: plistlib.dump(p,f)
PY
chmod +x "$APP_DIR/Contents/MacOS/phinbox" "$APP_DIR/Contents/Resources/inbox-helper"
printf 'Assembled: %s\n' "$APP_DIR"
