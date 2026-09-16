# Per-OS Icon Spec — BytePort

**Status:** PROPOSED (no assets generated yet)
**Date:** 2026-06-04
**Author:** L1 worker (apps registry audit)

## Current state (measured)

- `frontend/web/src-tauri/icons/` already has a Tauri-conventional icon set:
  32x32.png, 128x128.png, 128x128@2x.png, icon.icns, icon.ico, icon.png,
  plus Windows StoreLogo sizes (Square*.png).
- No hand-authored `assets/brand/logo.svg` source of truth.
- No platform material-language variants (android-glass, macos-liquid, windows-mica).

## Why this spec

Tauri's default icon set is a flat raster. Per Phenotype platform_icon_materials
doctrine, BytePort should ship a hand-authored SVG base + 3 platform-tuned
variants (one per OS material language) + a multi-resolution .ico for Windows.

## Base vector

Hand-authored SVG at `assets/brand/logo.svg` — a port-shaped mark
(a network port / socket silhouette) with a small "byte" glyph inside
(8 dots in a 2x4 grid, suggesting the byte). Glassmorphism cues: stacked
colored glass layers, light refraction edge.

## Per-OS variants

| OS         | File                                          | Size          | Material language |
|------------|-----------------------------------------------|---------------|-------------------|
| macOS      | `assets/brand/macos/icon-1024.icns`           | 1024x1024     | Liquid-glass (stacked stained glass + liquid blur) |
| macOS      | `assets/brand/macos/icon-512.png`             | 512x512       | Liquid-glass PNG fallback |
| Android    | `assets/brand/android/icon-512.png`           | 512x512       | Neo-glassmorphic (3D card, geisty) |
| Android    | `assets/brand/android/icon-foreground-432.png` | 432x432      | Adaptive icon foreground |
| Android    | `assets/brand/android/icon-background.png`    | 432x432       | Adaptive icon background |
| Windows    | `assets/brand/windows/icon.ico`               | 16/32/48/256  | Mica (stacked stained panes) |
| Windows    | `assets/brand/windows/icon-256.png`           | 256x256       | Mica PNG fallback |
| Web        | `frontend/web/static/favicon.ico`             | 16/32/48      | Glassmorphic |
| Web        | `frontend/web/static/apple-touch-icon.png`    | 180x180       | iOS home-screen |
| Tauri      | `frontend/web/src-tauri/icons/icon.png`       | 1024x1024     | (existing — regenerate from new SVG) |
| Tauri      | `frontend/web/src-tauri/icons/icon.ico`       | multi-res     | (existing — regenerate) |
| Tauri      | `frontend/web/src-tauri/icons/icon.icns`      | multi-res     | (existing — regenerate) |
| Social     | `assets/brand/social-512.png`                 | 512x512       | OG/Twitter card |

## AI-DD + renderers

- AI-CODED (hand-authored SVG, paths written by hand).
- Raster export: resvg (canonical), falling back to rsvg-convert → ImageMagick → Pillow.
- ICO assembly: ImageMagick fallback, else Pillow.
- .icns: iconutil (mac) or png2icns.
- Regenerate Tauri's icon.* from the new SVG via `cargo tauri icon assets/brand/logo.svg`.

## Out of scope (this PR)

- Generating the actual assets. A follow-up PR will land them.

## Open questions

- Is the Tauri icon set in `src-tauri/icons/` considered authoritative, or do we replace it with the new material-language versions? (Likely: regenerate from new SVG.)
