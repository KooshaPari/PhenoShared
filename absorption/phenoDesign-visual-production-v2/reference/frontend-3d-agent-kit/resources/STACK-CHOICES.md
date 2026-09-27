# Stack choices: a hierarchy, not an everything-bagel

These are kit recommendations based on the requested workflow. IDs resolve in SOURCES.md/catalog.json. Library status and licensing can change; inspect the exact installed versions.

## Default route for the rotating product

**Asset authoring:** Blender Python in a fresh local process (R05/R06). Code-first authoring is reproducible, inspectable and easy to rerun. Add a persistent MCP bridge only when it materially improves visual scene iteration, not because every agent workflow needs an MCP.

**Delivery:** glTF/GLB with named components, explicit axis/unit convention and a rest-transform contract. Use glTF Transform and Khronos Validator (R16/R17) as distinct tools: optimization versus conformance. Inspect with a second viewer (R18) and the target browser.

**Web:** Three.js directly, or R3F in an existing React product (R08/R09). GSAP ScrollTrigger is a suitable controller for complex scrubbed sequences (R10), while Motion/native progress often suffices for simpler choreography (R11/R12). Keep one owner of each animated property.

**Testing:** native source renders plus actual-browser interaction/frame capture (R22). Measure the true target GPU; the kit's CPU fallback and software-rendering tests are not representative FPS benchmarks.

## Alternatives that can be better

| Need | Prefer | What you give up |
|---|---|---|
| Static premium hero | High-quality render/photo + HTML | Arbitrary viewpoint and genuine inspection |
| Bounded camera narrative | Pre-rendered video/sequence | Live material changes and free rotation; decoded memory/seek budget still matter |
| Simple product inspection | model-viewer | Some bespoke scene/material choreography |
| Interactive vector props | SVG/Rive | Volumetric product rendering |
| Simple UI motion | CSS or Motion | Complex scene-specific timelines |
| Regular hard-surface concept | Procedural Blender/mesh code | Automatic arbitrary organic reconstruction |
| Organic concept from references | Optional local image-to-3D | Predictable topology, functional parts, exact hidden geometry and cheap cleanup |

No recommendation requires React, a physics engine, WebGPU, postprocessing, scroll smoothing or a remote generation API by default. Add one because it solves a measured design problem.

## What this kit's demos mean

The no-dependency reference demonstrates editable generated geometry, deterministic story state and input/fallback patterns. It includes a tiny WebGL2 shader and an approximate Canvas2D triangle renderer. Neither is a general production rendering framework. The CPU preview can be slow and exhibit painter-order artifacts at intersections. Prefer a poster on a constrained production device.

The separate Three/GSAP adapter shows the intended framework boundary. Dependencies were unavailable in this environment; its runtime is NOT_RUN. It has no fabricated lockfile or claimed production benchmark. Install approved packages explicitly on the user's machine, pin the resulting versions, run it and retain evidence.
