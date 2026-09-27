# Remotion: a rendering and presentation layer, fully integrated with journeys

## What belongs here

Programmatic product films, annotated actual walkthroughs, documentation clips, title/diagram animation and aspect-ratio derivatives. Preserve TSX, annotation specs and input assets. Interactive page behavior should remain in its real runtime; a video is not a replacement for a drag/scroll/stateful experience.

## Existing migration and supplied changes

PR87 introduces `remotion/doc-embeds`, including a generic composition, capture/conversion scripts and annotations. The overlay replaces rendering/staging, scene mapping and finite highlight timing while preserving the DocEmbed identifier and the existing Callout component. Source metadata becomes mandatory at the render stage; the safe staging wrapper supplies measured dimensions.

Strict changes are intentional: explicit still/video duration, contained local asset paths, bounded dimensions/timing and no network downloads during render. Older specs that depended on four-second defaults, absolute asset paths or implicit copying must be migrated explicitly. Prefer clear rejection to a plausible but incorrect film.

The renderer uses Remotion's bundler/selectComposition/renderMedia APIs instead of shelling through npx. It requires an existing browser path in DOC_EMBEDS_BROWSER, probes streams with FFprobe, isolates staging/output, verifies encoded outputs with FFmpeg, and returns export integrity separately from visual/consumer verification. Its JSON receipt intentionally leaves E2E INCONCLUSIVE.

## On-device dependency and execution gate

The installer adds the Remotion workspace and direct bundler dependency but does not fetch packages. Align `remotion` and every `@remotion/*` package to one tested version using the actual lockfile. Confirm commercial terms for the user/organization/use case. Acquire official upstream skills through the catalog and review their permissions/provenance.

```sh
# In the integrated real repository after dependency qualification:
node --test packages/visual-production/test/*.test.mjs
# Set DOC_EMBEDS_BROWSER to the actual installed qualified executable via your shell's environment mechanism.
node remotion/doc-embeds/bin/render.mjs --annotations /owned/job/annotations.json --out /owned/job/exports --format mp4
```

SSR does not automatically apply remotion.config.ts. Port any required custom configuration explicitly and test it. The canary bundles in each isolated run; production should cache an immutable bundle using source/config/lock identity and serve immutable job assets safely. Do not trade race-free behavior for a shared mutable public directory.

## Required real render fixtures

Use source images with visible corner markers and unequal aspect ratios. Test both cover and contain with source-space highlights, camera zoom endpoints and scene-local duration. Render frame 0, annotation-start minus/at/plus one, annotation-end minus/at/plus one, scene transitions and final frame. Compare marker coordinates in rendered pixels, not only math-unit outputs.

Render video with and without audio, mixed source dimensions, captions at mobile size, odd-size output rejection, path/name collisions and two concurrent jobs. Check actual stream duration, orientation/pixel aspect assumptions, frame cadence, black/blank frames, decoded audio and full playback in the consuming viewer. Include missing browser/package, failed decode and cancelled export cases.

## Remaining known work

Recorder manifest-root differences, fallback HTML vs ARIA typing and swallowed capture failures are not fixed by this rendering overlay. Extend the existing schemas/converter/viewer together and run real journey-to-embed-to-consumer tests. `evidence/VALIDATION.md` explicitly records that complete Remotion runtime execution was unavailable here. Pure functions, syntax and a synthetic FFmpeg clip cannot substitute for that gate.
