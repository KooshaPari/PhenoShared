#!/usr/bin/env bash
set -euo pipefail

# build.sh — Build Phinbox.app bundle for macOS
#
# Usage: ./build.sh [--release]
#
# Creates Phinbox.app in apps/phinbox-app/dist/ with:
# - phinbox-app binary (compiled with tray-native feature)
# - Info.plist
# - AppIcon.icns (generated from placeholder)
#
# The .app can be dragged to /Applications or run directly.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
APP_NAME="Phinbox"
BUNDLE_DIR="$SCRIPT_DIR/dist/${APP_NAME}.app"

PROFILE="debug"
CARGO_FLAGS=""
if [[ "${1:-}" == "--release" ]]; then
    PROFILE="release"
    CARGO_FLAGS="--release"
fi

echo "==> Building phinbox-app binary (features: mcp, tray-native) ..."
cd "$REPO_ROOT"
cargo build -p phinbox --bin phinbox-app --features "mcp,tray-native" $CARGO_FLAGS

# Build the Swift inbox helper
SWIFT_SRC="$SCRIPT_DIR/Sources/inbox-helper"
if [[ -f "$SWIFT_SRC/main.swift" ]]; then
    echo "==> Building inbox-helper (Swift native window) ..."
    swiftc -o "$REPO_ROOT/target/${PROFILE}/inbox-helper" \
        "$SWIFT_SRC/main.swift" \
        -framework Cocoa -framework WebKit \
        -parse-as-library
    echo "  inbox-helper built successfully"
else
    echo "  WARNING: Swift inbox helper source not found at $SWIFT_SRC/main.swift"
    echo "  The .app will fall back to opening the browser"
fi

# Locate the built binary
if [[ "$PROFILE" == "release" ]]; then
    BIN_SRC="$REPO_ROOT/target/release/phinbox-app"
else
    BIN_SRC="$REPO_ROOT/target/debug/phinbox-app"
fi

if [[ ! -f "$BIN_SRC" ]]; then
    echo "ERROR: binary not found at $BIN_SRC"
    exit 1
fi

echo "==> Assembling ${APP_NAME}.app bundle ..."
rm -rf "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR/Contents/MacOS"
mkdir -p "$BUNDLE_DIR/Contents/Resources"

# Copy Info.plist
cp "$SCRIPT_DIR/Info.plist" "$BUNDLE_DIR/Contents/Info.plist"

# Copy the binary and rename to match CFBundleExecutable
cp "$BIN_SRC" "$BUNDLE_DIR/Contents/MacOS/phinbox"
chmod +x "$BUNDLE_DIR/Contents/MacOS/phinbox"

# Copy the Swift inbox helper to Resources
INBOX_HELPER="$REPO_ROOT/target/${PROFILE}/inbox-helper"
if [[ -f "$INBOX_HELPER" ]]; then
    cp "$INBOX_HELPER" "$BUNDLE_DIR/Contents/Resources/inbox-helper"
    chmod +x "$BUNDLE_DIR/Contents/Resources/inbox-helper"
    echo "  Copied inbox-helper to Resources"
fi

# Generate placeholder icon (16x16 PNG → icns)
ICON_PNG="$SCRIPT_DIR/dist/icon_512.png"
ICON_ICNS="$BUNDLE_DIR/Contents/Resources/AppIcon.icns"
mkdir -p "$SCRIPT_DIR/dist"

# Create a simple 512x512 PNG using built-in tools
# Use sips/Python to generate a basic icon
python3 -c "
import struct, zlib, io, os

SIZE = 512
pixels = bytearray()

for y in range(SIZE):
    pixels.append(0)  # filter byte
    for x in range(SIZE):
        cx, cy = x - SIZE//2, y - SIZE//2
        dist = (cx*cx + cy*cy) ** 0.5
        if dist < SIZE * 0.4:
            # Inside circle - gradient from blue to purple
            t = dist / (SIZE * 0.4)
            r = int(60 + t * 80)
            g = int(100 + t * 40)
            b = int(200 + t * 55)
            a = 255
        elif dist < SIZE * 0.42:
            # Border
            r, g, b, a = 255, 255, 255, 200
        else:
            r, g, b, a = 0, 0, 0, 0
        pixels.extend([r, g, b, a])

def create_png(data, w, h):
    def chunk(ctype, cdata):
        c = ctype + cdata
        crc = struct.pack('>I', zlib.crc32(c) & 0xffffffff)
        return struct.pack('>I', len(cdata)) + c + crc

    raw = zlib.compress(bytes(data))
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)
    return sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', raw) + chunk(b'IEND', b'')

png_data = create_png(pixels, SIZE, SIZE)
with open('$ICON_PNG', 'wb') as f:
    f.write(png_data)
print(f'Created {SIZE}x{SIZE} PNG icon')
" 2>/dev/null && echo "  Generated placeholder icon" || echo "  Skipping icon generation (Python not available)"

# Convert PNG to icns if iconutil is available
if command -v iconutil &>/dev/null && [[ -f "$ICON_PNG" ]]; then
    ICONSET="$SCRIPT_DIR/dist/AppIcon.iconset"
    mkdir -p "$ICONSET"

    for size in 16 32 64 128 256 512; do
        sips -z $size $size "$ICON_PNG" --out "$ICONSET/icon_${size}x${size}.png" &>/dev/null
        double=$((size * 2))
        if [[ $double -le 1024 ]]; then
            sips -z $double $double "$ICON_PNG" --out "$ICONSET/icon_${size}x${size}@2x.png" &>/dev/null
        fi
    done

    iconutil -c icns "$ICONSET" -o "$ICON_ICNS" 2>/dev/null && echo "  Generated .icns icon" || echo "  Using placeholder icon"
    rm -rf "$ICONSET"
else
    echo "  iconutil not available — .app will use default icon"
fi

echo ""
echo "==> Done!"
echo "  App bundle: $BUNDLE_DIR"
echo ""
echo "  To install:"
echo "    cp -R \"$BUNDLE_DIR\" /Applications/"
echo ""
echo "  To run:"
echo "    open \"$BUNDLE_DIR\""
echo ""
echo "  Or run the binary directly:"
echo "    $BUNDLE_DIR/Contents/MacOS/phinbox"
