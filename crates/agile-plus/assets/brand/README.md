# AgilePlus Brand

**AI-CODED, not AI-generated.** The mark is hand-authored as a vector
[`logo.svg`](./logo.svg) (paths/shapes written by hand). No image-generation
model was used. Raster formats are exported deterministically from the SVG.

## The mark

A continuous **agile-sprint loop** (blue→purple ring + clockwise arrowhead =
iterative delivery) embracing **ascending velocity bars** (teal→green =
burnup/throughput), with a white **plus** accent (the "Plus" in AgilePlus),
on a dark rounded app tile.

## Files

| File | Purpose |
|------|---------|
| `logo.svg` | Source of truth (hand-coded vector) |
| `logo-{16,32,48,128,256,512}.png` | Raster sizes |
| `logo.png` | Canonical 512px PNG |
| `logo.jpg` | 512px, white matte |
| `app.ico` | Multi-resolution Windows icon (16/32/48/256) — feeds the Start-Menu / desktop shortcut |
| `logo-animated.svg` | L101 motion variant — SMIL rotating sprint-loop + sequential velocity bars (no JS) |

## Regenerating

```powershell
pwsh tools/Export-Brand.ps1
```

Renderer preference matches the Civis pure-Rust SVG convention
(`docs/research/RND-016-svg-pipeline-validation.md`): **resvg** (canonical),
falling back to `rsvg-convert` → ImageMagick → Python/cairosvg+Pillow.
ICO/JPG assembly uses ImageMagick when present, else Pillow.

## Per-OS icon export placeholder

The standing backlog per-OS icon pipeline lives at
`tools/build-icons/Build-Icons.ps1` and reads
`assets/brand/source/icon.svg`.

TODO: `assets/brand/source/icon.svg` is only a placeholder. Replace it with the
approved AgilePlus icon design before treating the generated `.ico`, `.icns`, or
`.png` assets in `assets/brand/generated/icons/` as release-ready.

## Motion variant (L101)

`logo-animated.svg` ships a 4-second loop:

- The agile-sprint loop (blue→purple ring + arrowhead) rotates clockwise 360° per 8s (half the
  loop period — visually pairs with the bars).
- The three velocity bars pulse upward in sequence (0s / 0.3s / 0.6s offsets), reading as a
  burnup burndown.
- Loop is seamless: last frame == first frame.

All animation is SVG-native SMIL — no JavaScript, no external CSS. Safe to inline in HTML, SVG
`<img src>`, README previews, and the splash banner.
