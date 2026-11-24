# Validation report

Prepared 15 September 2026. This is evidence for the shipped kit, not evidence from the user's machine or a claim of commercial art approval.

## Executed and passed

- **25 Python unit tests:** deterministic geometry, checked-in GLB/generator agreement, manifest hashes, narrow GLB/accessor/index/normal checks, corrupted/truncated/duplicate-name negative tests, skill sync dry-run/conflict/symlink/path traversal checks, actual temporary-project skill install preserving AGENTS.md, upstream blob identity, and package invariants. See `unit-tests.txt`.
- **21 / 21 browser checks:** actual generated-mesh pixels and state, scroll construction/reverse, manual rejoin at mid-story, material pixel changes, keyboard rotation, pause, idle/offscreen behavior, mobile overflow, reduced motion, no-JS and injected no-renderer fallback. See `browser-results.json` and `browser-tests.txt`.
- **10 Python files parsed/compiled**, including the Blender script without importing bpy. All shipped JavaScript files passed `node --check`; this is syntax, not runtime proof. See `syntax-results.json`.
- The generated asset manifest passed the supplied JSON Schema with Python jsonschema. See `schema-results.json`.
- Anthropic frontend-design `SKILL.md` matched upstream Git blob `a5333457c414d20d625f307df945842c0952ecc3` exactly.

## Actual browser environment and method

Chromium **144.0.7559.96**, disposable Linux test worker. The environment rejected ordinary file/loopback navigation with `ERR_BLOCKED_BY_ADMINISTRATOR` and did not expose WebGL. The test used explicit disposable-CI no-sandbox/software-ANGLE flags recorded in browser-results.json. The shipped test defaults to normal sandboxing and no forced software GL unless those flags are supplied. The test injected the **actual self-contained HTML** with Playwright `set_content` and exercised the real JavaScript/DOM/Canvas2D renderer. It did not mock successful drawing. Standalone mode issued zero external resource requests.

The renderer used for all graphics screenshots was **CPU triangle preview (WebGL unavailable)**. The rendered geometry is the original mesh included in the kit. The CPU path uses approximate triangle shading/depth sorting and is intended for inspection, not high-performance production fallback. Prefer a poster on constrained production hardware. No FPS or GPU benchmark is claimed.

## Explicitly not executed / blocked

| Capability | Status | What remains |
|---|---|---|
| Blender native build, .blend save, Cycles rendering, Blender GLB export | BLOCKED_ENV | No Blender/bpy available. Run the reviewed headless job on the user's worker and inspect its receipt/renders. |
| Tiny WebGL2 reference shader compilation/rendering | BLOCKED_ENV | No WebGL context available. Test on real compatible browsers. |
| Three.js + GSAP/Vite adapter install/build/runtime | NOT_RUN | Network/package dependencies were unavailable. Install approved exact versions and retain the real lockfile/results. |
| Khronos standards validator | NOT_RUN | Run independent conformance validation; kit audit is narrower. |
| File/HTTP navigation integration | BLOCKED_ENV | Navigation policy blocked it; document injection does not certify serving/base paths or deployment. |
| macOS/Windows Blender/MCP/CUDA/Metal workers | NOT_RUN | No claim of platform compatibility beyond source design intent. |
| Real touch device, full accessibility audit, GPU frame-time targets | NOT_RUN | Emulated viewport and keyboard tests do not replace those checks. |
| Local image-to-3D models and Geometry Nodes implementation | NOT_RUN | Resource/recipe guidance only; no weights downloaded or node graph falsely certified. |

## Captures

`desktop-start.png`, `desktop-exploded.png`, `mobile-start.png`, `mobile-reduced-motion.png`, `mobile-no-js.png`, `mobile-no-renderer.png` are actual browser screenshots. The no-renderer case intentionally injects context failure; it is marked as a test fixture. The offscreen test adds a temporary spacer to place the stage fully outside the viewport; that spacer is not shipped in the page. No captures were beautified or generatively retouched.

## Visible limitations and next quality pass

The trainer is stylized procedural concept geometry, not a scan or final photoreal product. It has constructive overlaps, no canonical UV maps, simplified materials and approximation artifacts in the CPU preview. Side support placement was revised after actual screenshot inspection; remaining topology/close-up quality belongs in the Blender art pass. The exported GLB is approximately 654.4 KiB, with 25,900 triangles and 47 named nodes. These are asset measurements, not performance guarantees.

A finished campaign still needs art-directed native source, cleanup/baking, browser material parity, licensed product inputs, real-device testing and product-owner approval.
