#!/usr/bin/env bash
# Build all brand assets from SVG → PNG → icns.
# Pure SVG authoring → magick render → Apple .icns.
#
# Prerequisites: ImageMagick (`magick`), `iconutil` (Xcode CLT), `rsvg-convert`
# (optional fallback). Run from anywhere — paths are absolute.

set -euo pipefail

ROOT="${SESSION_LEDGER_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
ASSETS="${ROOT}/assets"
BUILD="${ROOT}/build"
DIST="${ASSETS}/dist"
rm -rf "${BUILD}" "${DIST}"
mkdir -p "${BUILD}/icns" "${BUILD}/png" "${DIST}/icons-2.5d" "${DIST}/icons-line" "${DIST}/og" "${DIST}/social" "${DIST}/dock"

log() { printf "%s\n" "$*"; }
fail() { log "✗ FAIL: $*"; exit 1; }

# --- PNG sizes required for Apple .icns ---
ICON_SIZES=(16 32 64 128 256 512 1024)
# Retina (@2x) variants
RETINA_SIZES=(32 64 128 256 512 1024)

render_svg() {
    local svg="$1" dst="$2" size="$3"
    if command -v rsvg-convert >/dev/null 2>&1; then
        rsvg-convert -w "$size" -h "$size" "$svg" -o "$dst"
    else
        magick -background none -density "$((size * 3))" "$svg" -resize "${size}x${size}" "$dst"
    fi
}

# --- 1. Build the iconset for the app icon ---
log "═══ 1. App icon (32 SVG → 16 PNG → icns) ═══"
ICONSET_DIR="${BUILD}/sessionledger.iconset"
rm -rf "${ICONSET_DIR}"
mkdir -p "${ICONSET_DIR}"

# Use the 2.5D mascot at 1024 as the master icon
MASTER_SVG="${ASSETS}/brand/mascot/getta-base.svg"
[[ -f "${MASTER_SVG}" ]] || fail "Missing ${MASTER_SVG}"

for size in "${ICON_SIZES[@]}"; do
    out="${ICONSET_DIR}/icon_${size}x${size}.png"
    render_svg "${MASTER_SVG}" "${out}" "${size}"
    log "  · ${size}x${size}"
done

# --- 2. Generate the .icns ---
ICNS_OUT="${DIST}/SessionLedger.icns"
iconutil -c icns -o "${ICNS_OUT}" "${ICONSET_DIR}" || fail "iconutil failed for ${ICNS_OUT}"
log "  ✓ ${ICNS_OUT}"

# --- 3. Build the flat 2.5D tab icons (PNG @ 2x for retina) ---
log "═══ 2. 2.5D tab icons + status icons @ 2x ═══"
for svg in "${ASSETS}/icons/2.5d"/*.svg; do
    [[ -f "${svg}" ]] || continue
    name=$(basename "${svg}" .svg)
    render_svg "${svg}" "${BUILD}/png/icon25d-${name}.png" 128
    cp "${BUILD}/png/icon25d-${name}.png" "${DIST}/icons-2.5d/${name}@2x.png"
    render_svg "${svg}" "${BUILD}/png/icon25d-${name}-1x.png" 64
    cp "${BUILD}/png/icon25d-${name}-1x.png" "${DIST}/icons-2.5d/${name}.png"
    log "  · ${name}"
done

# --- 4. Build the line icon set ---
log "═══ 3. Line icons @ 2x ═══"
for svg in "${ASSETS}/icons/line"/*.svg; do
    [[ -f "${svg}" ]] || continue
    name=$(basename "${svg}" .svg)
    render_svg "${svg}" "${BUILD}/png/iconline-${name}.png" 64
    cp "${BUILD}/png/iconline-${name}.png" "${DIST}/icons-line/${name}@2x.png"
    render_svg "${svg}" "${BUILD}/png/iconline-${name}-1x.png" 32
    cp "${BUILD}/png/iconline-${name}-1x.png" "${DIST}/icons-line/${name}.png"
    log "  · ${name}"
done

# --- 5. Marketing assets ---
log "═══ 4. Marketing assets (hero, OG, social, dock) ═══"
declare -A MKT_SIZES=(
    ["hero/hero-1200x630"]="1200x630"
    ["og/og-card"]="1200x630"
    ["social/twitter-card"]="1200x675"
    ["social/mobile-card"]="1080x1920"
    ["dock/dock-tile"]="256x256"
)

for path in "${!MKT_SIZES[@]}"; do
    size="${MKT_SIZES[$path]}"
    svg="${ASSETS}/brand/${path}.svg"
    [[ -f "${svg}" ]] || { log "  ! skip ${path} (missing)"; continue; }
    out_dir="${DIST}/marketing/${path%/*}"
    mkdir -p "${out_dir}"
    W="${size%x*}"; H="${size#*x}"
    render_svg "${svg}" "${DIST}/marketing/${path%/*}/$(basename ${path}).png" 1024 || \
        magick -background none -density 300 "$svg" -resize "${W}x${H}" "${DIST}/marketing/${path%/*}/$(basename ${path}).png"
    log "  · ${path} (${size})"
done

# --- 6. Mascot pose variants ---
log "═══ 5. Mascot pose variants (PNG) ═══"
for svg in "${ASSETS}/brand/mascot"/*.svg; do
    [[ -f "${svg}" ]] || continue
    name=$(basename "${svg}" .svg)
    render_svg "${svg}" "${DIST}/mascot/${name}.png" 512
    log "  · ${name}"
done

# --- 7. Summary ---
log ""
log "═══ Build complete ═══"
log "App icon:     ${ICNS_OUT}"
log "2.5D icons:   ${DIST}/icons-2.5d/   ($(ls ${DIST}/icons-2.5d/ | wc -l | tr -d ' ') files)"
log "Line icons:   ${DIST}/icons-line/   ($(ls ${DIST}/icons-line/ | wc -l | tr -d ' ') files)"
log "Marketing:    ${DIST}/marketing/"
log "Mascot:       ${DIST}/mascot/        ($(ls ${DIST}/mascot/ 2>/dev/null | wc -l | tr -d ' ') files)"
log ""
log "Install: cp ${ICNS_OUT} /Applications/SessionLedger.app/Contents/Resources/AppIcon.icns"
