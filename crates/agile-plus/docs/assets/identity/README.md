# AgilePlus — Identity Demo Media (L105)

Animated SVG + MP4 showcasing the [Backbone-2 lab-graphite + pulse-green palette](../../assets/tokens.css) in motion.

## Files

| File | Purpose |
|---|---|
| `demo.svg` | 480×270 animated SVG — pulse heartbeat + scanline + orbit ring (looped CSS animation, ~5s) |
| `demo.mp4` | H.264/MP4 rendered from `demo.svg` via ffmpeg (24fps, 5s loop) |

## Palette (Backbone-2 — lab-graphite + pulse-green)

- Outer background `#0a0d12`
- Inset panel `#161b22`
- Pulse-green `#3fb950` (dominant — process heartbeat)
- Warm-amber `#d29922` (single hot pixel — cooldown)

## Animation

- Core pulse: cubic-bezier scale 0.85 → 1.18 → 0.95 → 1.04 (heartbeat rhythm)
- Orbit ring: 6s linear rotation (process tracker)
- Scanline: 3.4s vertical sweep (monitor readout)

## Render command

```sh
ffmpeg -y -i demo.svg -vf "fps=24,format=yuv420p,scale=480:270" \
  -c:v libx264 -pix_fmt yuv420p -movflags +faststart demo.mp4
```

## Source of truth

- Tokens: [`../../assets/tokens.css`](../../assets/tokens.css)
- Source icon: [`../../assets/brand/source/icon.svg`](../../assets/brand/source/icon.svg)
- Scorecard: `.claude/audit/.vision/L96-L107.md`