---
name: pd-photoshop-raster
description: "Author layered raster compositions, masks, textures and image derivatives using a qualified Photoshop host."
license: MIT (original guidance; linked tools and assets keep their own licenses)
---

# Photoshop Raster

Use Photoshop for compositing, retouching, masks, smart objects and layered raster handoff; use a simpler image pipeline for resize/encode-only tasks. Start from rights-cleared sources and a target color/alpha contract. Work nondestructively: retain source layers, masks and adjustments; name layers by purpose instead of copy-number suffixes.

Photoshop UXP operations that mutate documents belong in awaited executeAsModal calls. Serialize commands within an owned host session and preserve cancellation. The supplied UXP prototype accepts bounded local raster-composition jobs after a workspace grant; it is not a general arbitrary-code service and has not been host-qualified in this package's preparation environment.

Import only staged files, associate the new document with its job, save a layered PSD, then export a PNG/WebP/JPEG derivative appropriate to alpha and placement. Never silently discard a color profile, flatten the only source, or treat an API return as pixel proof. For complex batchPlay operations, record descriptors against the installed host and validate a minimal case before bulk use.

Native acceptance requires cold reopen, expected layer/mask inventory, no missing links, correct dimensions and independent export inspection. Test transparency over dark and light backgrounds, edges at native scale, and downsampled detail. Evidence screenshots are immutable; make presentation edits only to clearly identified derivatives.

## Related contracts

Read the repository's `docs/visual-production/E2E-CONTRACT.md`, `ALL-FORMS.md`, and source catalog for the selected tool. In the standalone kit these are under `docs/` and `resources/`. Preserve exact failure/blocked states and the existing source/evidence owners.
