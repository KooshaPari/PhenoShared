# SessionLedger — Identity Demo Media (L105)

Animated SVG + MP4 showcasing the [Lab-Coat palette](../../../assets/tokens.css) in motion.

## Files

| File       | Purpose                                                                                                             |
| ---------- | ------------------------------------------------------------------------------------------------------------------- |
| `demo.svg` | 480×270 animated SVG — Erlenmeyer flask + bubbles + Bunsen burner + session-bundle bars (looped CSS animation, ~5s) |
| `demo.mp4` | H.264/MP4 rendered from `demo.svg` via playwright + ffmpeg (24fps, 5s loop)                                         |

## Palette (Lab-Coat — cobalt + orange-500)

- Outer background `#f6f8fa` (lab coat white)
- Bench grid `#1f2937` (slate)
- Cobalt `#2563eb` (primary — slide-stain blue, bundle bars, liquid)
- Orange `#f97316` (live session — lit Bunsen burner)
- Yellow `#facc15` (bubbles — growth-medium)
- Teal `#14b8a6` (secondary — available in palette)

## Animation

- Bubbles: 3.2s ease-in rise from liquid surface to flask neck, 6 bubbles staggered 0.4s
- Bunsen flame: 1.8s ease-in-out scale + translateY flicker
- Bundle bars: 2s ease-in-out opacity breathing (active session indicator)

## Render command

```sh
python /tmp/svg2mp4.py demo.svg demo.mp4 480 270 24 5
```

## Source of truth

- Visual acceptance: [`../../VISUAL_SPEC.md`](../../VISUAL_SPEC.md) (palette, empty/loading/error, motion)
- Golden checklist: [`../../../tests/visual/README.md`](../../../tests/visual/README.md)
- Tokens: [`../../../assets/tokens.css`](../../../assets/tokens.css)
- Source icon: [`../../../assets/brand/sessionledger-icon.svg`](../../../assets/brand/sessionledger-icon.svg)
- Scorecard: `.claude/audit/.vision/L96-L107.md`
