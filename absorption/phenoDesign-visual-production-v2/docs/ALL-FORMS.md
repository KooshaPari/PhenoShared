# All-forms coverage and medium selection

**The scope is the full creative workflow, not “frontend CSS plus a Blender hero.”** A capability has four distinct stages: authorable source, export/interchange, runtime/consumer, and verified delivery. The matrix is a routing specification; it is not a certification that every tool has already run on the user's machine.

| Form | Authoring candidates | Retained editable source | Delivery/consumer | Required specific verification |
|---|---|---|---|---|
| Layout/type/UI | Existing phenoDesign system, HTML/CSS, design tools as needed | Tokens, styles, semantic component source | Real app/docs/landing UI | Overflow, reading order, focus, contrast, long text, zoom, loading/error states |
| Vector art/marks/icons | Illustrator; SVG/Inkscape for simpler automation | .ai, semantic SVG, script/data | SVG, raster sizes, inline interactive SVG | Artboards, path shape, small-size clarity, no unsafe external SVG content |
| Raster/photography/compositing | Photoshop; Krita or simpler imaging tools | PSD/PSB/KRA, masks, layers, sources | PNG/WebP/AVIF/JPEG and consumer | Reopen, layers, links, color/alpha, artifacts, actual scaling |
| Surface/material work | Photoshop/Krita + Blender procedural materials | Layered texture sources, node graphs, texture metadata | PBR textures, bakes, material definitions | Channel space, normal basis, UV seams, mip behavior, target renderer |
| Editorial/print/packaging | Illustrator or a qualified layout/CAD tool | Native page/layout/artboard source | Vendor-specified PDF/assets | Trim/bleed/safe area, missing links, output profile, actual-size proof |
| Diagrams/data stories | SVG/D3/graph tools; Manim/Motion Canvas | Data/query + diagram/scene code | Static, interactive or video explanation | Data/semantic correctness, labels, hierarchy, accessible equivalent |
| Frame-by-frame/pixel art | Krita, sprite editor, Grease Pencil | Timeline/cels/rig source | Frames/atlas/video | Frame timing, anchors, atlas bleed, alpha, interruption/loop seam |
| Rigged vector/characters | Rive CLI/editor or qualified vector rig workflow | RML/project/editor source and rig | .riv + runtime | Named state inputs, interrupt/recovery, artboard scale, lifecycle/accessibility |
| Timeline vector motion | AE/exporter or code-authored supported vectors | Original timeline and export recipe | Lottie JSON or dotLottie | Supported effects, masks, easing, text, first/last/loop/runtime frames |
| 2.5D/layered product effects | SVG/CSS/Canvas; layered raster or Blender renders | Layer hierarchy/depth map/animation source | Parallax, cutaways, composited scenes | Honest depth assumptions, crop, pointer/scroll response, reduced motion |
| Full 3D/products/scenes | Blender scripts/Geometry Nodes; suitable acquired DCC | .blend, scripts, rigs, textures, parameters | GLB/glTF, images, animation | Scale/axes, topology/normals, materials, animation, renderer fidelity |
| Procedural/shaders/particles | Existing graphics SDK + GLSL/WGSL/Canvas tools | Shader/source/seed/config | 2D/3D runtime or rendered media | Deterministic captures, color/alpha, context loss, cleanup/performance |
| Motion graphics/video | Remotion, AE, Motion Canvas, FFmpeg as appropriate | TSX/scene source, AEP, timelines, inputs | MP4/WebM/master/derivatives | Frames/duration, audio, captions, crop, full decode, actual player |
| Sound/narration | Existing licensed audio tools/FFmpeg; approved synthesis | Session/cues/original tracks | Encoded audio or muxed media | Rights, timing, intelligibility, clipping/loudness, user-controlled playback |
| Spatial/AR/XR | Blender/OpenUSD tooling + target runtime | Scene, units, hierarchy, interaction source | Qualified spatial viewer/device | Real device scale/input/tracking, comfort, fallback, not a desktop-only claim |
| Generated assets | Qualified local workflows or approved hosted services | Workflow, model/input versions, repair source | The appropriate production pipeline above | Rights, source consistency, repair, reproducibility limits, no fabricated evidence |

## What “all” does not mean

It does not mean every file extension can round-trip losslessly, every Adobe feature has a script API, every plugin is safe, or all forms should appear on every page. It means a new need has an explicit authoring/delivery/validation route and a way to extend the shared system. Unsupported adapters have a visible qualification backlog rather than being disguised as working features.

## Default selection

Use existing design tokens and standard DOM first for UI. Use vector masters for vector geometry, layered raster for compositing, and real scene sources for spatial products. Prefer Illustrator/Photoshop when their editability or functionality earns the host requirement. Use Blender for reproducible full 3D. Use Remotion for code-driven films and evidence-derived presentations, not as a universal replacement for drawing, editing, capture or interactive runtimes. Rive is particularly relevant for code-authored rigged 2D stateful props under the currently documented CLI workflow. [A01–A12, M01–M08, R01–R02 in the source catalog.]

The browser runtime, video renderer and authoring DCC can share parameters and asset identity without becoming one monolithic engine. That is the consolidation target.
