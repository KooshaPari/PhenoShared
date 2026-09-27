---
name: pd-illustrator-vector
description: "Create editable Illustrator vector artwork, icon systems, diagrams and product illustration with native scripts."
license: MIT (original guidance; linked tools and assets keep their own licenses)
---

# Illustrator Vector

Use Illustrator when editable paths, shape construction, artboards and designer handoff matter. Prefer direct SVG/Inkscape for small deterministic web vectors where an Adobe host adds no value. Probe the installed Illustrator scripting environment; do not assume Photoshop UXP is Illustrator's scripting API.

Author semantic layers and named objects. Establish top-left design coordinates and convert them consistently to Illustrator artboard coordinates. Construct a silhouette first, then deliberate contour weight, negative space and detail. Keep text live in the master where possible; resolve font substitutions explicitly and never bundle installed font binaries. Preserve a separate outline delivery derivative when required.

Use the supplied data-to-JSX compiler as a bounded authoring canary, not as a quality ceiling. Extend native scripting through reviewed operations rather than accepting arbitrary script text in untrusted jobs. Save .ai before export, then produce SVG and raster previews. Never modify the operator's current document by relying on activeDocument.

Reopen .ai in a clean owned document and verify named layers, paths, bounds, color mode and fonts. Inspect the exported SVG at the intended size, on both background polarities, and inside the actual browser. Reject unexpected rasterization, clipping, thin lost strokes, embedded scripts or external references. A successful export dialog is not E2E acceptance.

## Related contracts

Read the repository's `docs/visual-production/E2E-CONTRACT.md`, `ALL-FORMS.md`, and source catalog for the selected tool. In the standalone kit these are under `docs/` and `resources/`. Preserve exact failure/blocked states and the existing source/evidence owners.
