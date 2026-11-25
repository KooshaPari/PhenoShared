# focus-icon-gen

Procedural app icon generator for FocalPoint. Renders a flame icon inspired by the Coachy mascot using pure Rust pixel manipulation. Produces PNG output with configurable gradient backgrounds and flame shape parameters.

## Purpose

Generates deterministic app store icons at build time. Embeds Coachy's visual identity (flame silhouette, color palette, gradient) into icon assets without needing external design tools or hand-coded image files. Used in fastlane asset pipelines for iOS and Android app store submissions.

## Key Types

- `IconRenderer` — canvas-based pixel painter
- `FlameShape` — procedural geometry (silhouette, gradient, pixel ops)
- `ColorPalette` — extracted from Coachy design tokens
- `PngEncoder` — output to file

## Entry Points

- `generate_icon()` — render icon with default parameters
- `generate_icon_with_config()` — custom size, flame scale, background gradient
- `IconRenderer::new()` → `render_flame()` → `write_png()`

## Functional Requirements

- FR-APPSTORE-001 (Icon generation and versioning)
- Deterministic output (reproducible builds)
- No external dependencies (pure pixel manipulation)

## Consumers

- Build scripts / fastlane lanes (iOS, Android)
- App store submission pipelines
