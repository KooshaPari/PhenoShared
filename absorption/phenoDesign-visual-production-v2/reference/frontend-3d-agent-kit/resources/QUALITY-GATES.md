# Quality gates for ambitious product frontends

All numeric limits are **proposed starting policies**, not measurements or guarantees. Adjust them to actual audience hardware and product requirements. Use independent pass/fail gates rather than hiding a critical failure in an average aesthetic score.

| Gate | Required evidence | Failure example |
|---|---|---|
| Intent | One real product job and the information each motion beat reveals | Rotation exists only because the renderer can rotate |
| Form | Profile/three-quarter/rear clay views, recognizable silhouette | A logo or texture is doing all the recognition work |
| Construction | Named parts, correct pivots/rest transforms, inspected gaps | Explode animation tears unrelated geometry or moves all nodes together |
| Lookdev | Fixed-light material comparisons and browser export parity | Roughness, transparency or tone mapping differs unnoticed |
| Composition | Desktop/mobile screenshots, no clipping or text collision | Desktop camera merely cropped into portrait |
| Interaction | Forward/reverse/seek, direct buttons, keyboard/touch/reset | Accumulated rotation differs after reverse scroll |
| Accessibility | DOM baseline, visible focus, motion policy, no trap | Required content only exists in a canvas texture |
| Reliability | No-JS, missing assets, renderer failure, lifecycle tests | Blank hero or leaked render loops after route change |
| Performance | Measured transfer/startup/frame/idle/memory by environment | A desktop emulator is presented as mobile GPU evidence |
| Custody | Native source, generator, dependencies, rights and hashes | Only a GLB or screenshot remains; no editable source/license |

## Suggested initial budgets

Poster <=250 KiB; primary GLB <=3 MiB; initial first-view rich-media transfer <=4 MiB (including required decoders/textures); mobile-oriented geometry <=80k visible triangles; <=50 draw calls as a starting target; no render loop while idle, offscreen or hidden; 95th-percentile active frame <=33.3 ms for a modest baseline target. These are choices for the first test, not web standards. A high-end visual brief may justify different budgets with evidence.

The included seed has more separate nodes/materials than an optimized production hero; its count is intentional for editable construction and semantic tests. It is **not** represented as meeting every production budget. Consolidate only where doing so preserves interaction semantics, then retest.

## Required review viewpoints

Capture 0/25/50/75/100% of scroll and manual orbit extremes at desktop and portrait dimensions. Pause and inspect. Check cast/contact shadows, edges, texture seams, hidden surfaces, material legibility, text-safe space and bounds. A beautiful first frame is not enough.

## Falsification prompts for the agent

Could a static poster communicate this better? Is the material problem actually a lighting problem? Does a generated texture hide bad geometry? Does the motion still teach anything at reduced speed? Does the pipeline work from a clean state, or only because of warm caches? Did the test actually exercise the renderer named in the report?

Use PASS/FAIL/BLOCKED_ENV/NOT_RUN per check. Do not edit evidence pixels except for separately labeled explanatory annotations.
