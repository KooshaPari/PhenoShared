# SessionLedger brand assets

Source of truth: [`sessionledger-icon.svg`](sessionledger-icon.svg) (1024×1024, Lab-Coat palette).

## Palette (Lab-Coat, proposed 2026-07-06 by vision-pillar; amber hex revised 2026-07-06 per melosviz-3d overlap check)

| Token       | Hex       | Role                                                                                                                  |
| ----------- | --------- | --------------------------------------------------------------------------------------------------------------------- |
| lab-white   | `#f6f8fa` | Background + panel (lab-coat)                                                                                         |
| slate-900   | `#1f2937` | Panel/text base                                                                                                       |
| cobalt-blue | `#2563eb` | Primary accent — slide-stain blue, glassware blue                                                                     |
| orange-500  | `#f97316` | Live-session indicator — lit Bunsen burner (was `#f59e0b`; swapped to avoid MelosViz `--mv-warn` semantic divergence) |
| teal-cool   | `#14b8a6` | Secondary — growth-medium teal (bubbles)                                                                              |

## Files

| Path                                           | Format                                 | Use                                                                        |
| ---------------------------------------------- | -------------------------------------- | -------------------------------------------------------------------------- |
| `assets/brand/sessionledger-icon.svg`          | SVG 1024×1024                          | Source of truth                                                            |
| `assets/icons/sessionledger.iconset/`          | PNG 16/32/48/64/128/256/512/1024 + @2x | macOS `.icns` source                                                       |
| `assets/icons/sessionledger.ico`               | ICO multi-res 16/32/48/64/128/256      | Windows app icon                                                           |
| `assets/icons/sessionledger-256x256.png`       | PNG 256×256                            | Linux app icon                                                             |
| `assets/brand/sessionledger-icon-animated.svg` | SVG 1024×1024 (SMIL)                   | L101 motion variant — cobalt bubbles rising + amber meniscus pulse (no JS) |

## Mark

Stylized eye-piece lens (the observation ring) containing a flask silhouette. The flask holds cobalt-blue liquid with a single amber-orange meniscus drop — reads as a microscope eyepiece looking into a live flask = "observing an in-progress session". Teal bubbles rise in the cobalt liquid as the secondary accent. Slate reticle tick marks at the cardinal positions give a microscope/scope feel.

## Family position

- **Distinct from Tracera** (navy/teal/indigo) — Lab-Coat is light-mode (lab-white base), Tracera is dark.
- **Distinct from MelosViz** (warm orchestral) — Lab-Coat is cool cobalt + amber; MelosViz is warm pinks/violets.
- **Distinct from Backbone-2** (sharecli/substrate, infra family) — Lab-Coat is light, Backbone-2 is graphite. No color hex overlap.
- **Pairs with sl-viewer**: slate-900 panel color ties directly into the existing dark-mode Dioxus surface as a secondary background tint.

## Regeneration

```bash
# Re-export iconset from SVG (after editing sessionledger-icon.svg)
for sz in 16 32 48 64 128 256 512 1024; do
  rsvg-convert -w $sz -h $sz assets/brand/sessionledger-icon.svg \
    -o assets/icons/sessionledger.iconset/icon_${sz}x${sz}.png
done
for sz in 16 32 128 256; do
  doubled=$((sz*2))
  cp assets/icons/sessionledger.iconset/icon_${doubled}x${doubled}.png \
     assets/icons/sessionledger.iconset/icon_${sz}x${sz}@2x.png
done

# Rebuild .ico (Windows)
convert assets/icons/sessionledger.iconset/icon_{16,32,48,64,128,256}x{16,32,48,64,128,256}.png \
  assets/icons/sessionledger.ico

# Linux 256
cp assets/icons/sessionledger.iconset/icon_256x256.png assets/icons/sessionledger-256x256.png
```

## Bundle wiring (sl-viewer Cargo.toml `[package.metadata.bundle]`)

The Dioxus desktop/web viewer lives in `crates/sl-viewer`. The bundle metadata
goes on that crate's manifest:

```toml
[package.metadata.bundle]
name = "SessionLedger"
identifier = "ai.kooshapari.sessionledger"
icon = ["../../assets/icons/sessionledger.iconset"]
resources = []
category = "DeveloperTool"
short_description = "Session-bundle compiler + viewer"
long_description = "Hexagonal session-bundle compiler with Dioxus viewer for OKF streams."

## Motion variant (L101)

`sessionledger-icon-animated.svg` ships a 4-second loop:

- Three cobalt bubbles rise from the flask base to the meniscus, staggered by ~1.3s (clipped
  to the flask interior so they stay inside the liquid).
- The amber `#f97316` meniscus glow breathes (rx 48 → 72 → 48).
- Loop is seamless: last frame == first frame.

All animation is SVG-native SMIL — no JavaScript, no external CSS. Safe to inline in HTML, SVG
`<img src>`, and README previews.
```
