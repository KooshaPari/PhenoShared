#!/bin/bash
set -euo pipefail

# Phinbox .app bundle builder
# Creates a proper macOS .app bundle with both binaries

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/target/release"
APP_DIR="$SCRIPT_DIR/dist/Phinbox.app"

echo "Building Phinbox.app bundle..."

# Clean previous bundle
rm -rf "$APP_DIR"

# Create directory structure
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

# Copy binaries
cp "$BUILD_DIR/phinbox-app" "$APP_DIR/Contents/MacOS/phinbox"
cp "$BUILD_DIR/inbox-helper" "$APP_DIR/Contents/MacOS/inbox-helper"

# Copy Info.plist
cp "$SCRIPT_DIR/Info.plist" "$APP_DIR/Contents/Info.plist"

# Copy icon
if [ -f "$SCRIPT_DIR/Resources/AppIcon.icns" ]; then
    cp "$SCRIPT_DIR/Resources/AppIcon.icns" "$APP_DIR/Contents/Resources/AppIcon.icns"
elif [ -f "$BUILD_DIR/AppIcon.icns" ]; then
    cp "$BUILD_DIR/AppIcon.icns" "$APP_DIR/Contents/Resources/AppIcon.icns"
fi

# Make binaries executable
chmod +x "$APP_DIR/Contents/MacOS/phinbox"
chmod +x "$APP_DIR/Contents/MacOS/inbox-helper"

echo "Built: $APP_DIR"
echo "Contents:"
ls -la "$APP_DIR/Contents/MacOS/"
