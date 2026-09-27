# Actual validation boundary

Prepared September 15, 2026. See the retained logs/JSON and source scripts. No remote repository changes or deployments were performed.

| Lane | Result | What was actually exercised |
|---|---|---|
| JavaScript regression tests | **59 passed** | Runtime contracts, crop/contain/zoom geometry, source-coordinate mapping, frame windows/timelines, verdict combination, path/symlink restrictions, hashed staging, basename collisions and isolated parallel staging |
| Python tests | **20 passed** | Path and installer safeguards, additive apply/idempotence, conflict rejection, skill activation safety, Illustrator data compilation/rejection, real media decode and wrong/truncated media rejection |
| Browser component checks | **17 passed** | Real Chromium execution of the loaded SVG fixture: native keyboard/range inputs, forward/reverse values, rendered transform settling, accent state, interpolation toggle, reset, mobile layout, reduced motion and no-JS preview |
| Syntax/transpile | **13 source files passed** | JS/TS/TSX/native JSX parsing/transpilation only; not dependency-aware typechecking or host/API compatibility |
| Media output | **Decoded and metadata-checked** | Included synthetic 320×180, 30fps, two-second H.264/AAC calibration clip; expected audio present |
| Original 3D kit | **Preserved, not requalified** | Complete earlier kit and its historical results remain under reference/ |
| Native Illustrator/Photoshop/AE | **NOT EXECUTED** | Local host recipes/plugin source supplied; no native applications/session available here |
| Blender / Rive | **NOT EXECUTED** | Original Blender recipe/assets retained and current Rive route documented; no local executable qualification |
| Complete Remotion | **NOT EXECUTED** | Source inspected, replacement code prepared and pure helpers tested; React/Remotion packages and rendering browser workflow not installed/run here |
| Real PhenoDesign repository build / consumer journey | **NOT EXECUTED** | Connector source reads only; container clone/network unavailable; no actual checkout typecheck, integration build or hosted route test |

## Important limits

The 17 browser checks used Playwright `set_content` because this environment's browser policy blocks file/HTTP navigation. The real page markup/scripts render in Chromium, but that is component-level evidence, **not** an HTTP-route or deployed-product E2E claim. Mobile checks are viewport/input emulation, not a physical phone or screen-reader evaluation. No WebGL/GPU claim is inferred from SVG rendering.

The media calibration clip is synthetic test content, not a screen recording or a completed product film. FFprobe metadata plus FFmpeg decode do not establish perceptual quality, lip sync, correct narration or a real product journey. Export integrity remains separate from those checks.

Installer tests use temporary files/fixtures and verify safeguards. They do not prove a clean apply against an independently cloned live PR87 checkout. The installer includes exact inspected source blob guards and refuses current-source drift. Run dry-run, actual package typechecks and the receiving-agent backlog before adoption.

Native .ai/.psd/.aep/.blend/.riv production outputs were not manufactured or claimed. The code's native API details need installed-host validation. No app binaries, credentials or font files are shipped.

## Results and Observation Dates

Observation date for this section is `2026-09-15`, read from the `evidence/ITERATION-NOTES.md` file observation date. The iteration notes file carries no per-iteration dates, so individual iteration dates are recorded as UNKNOWN rather than inferred.

| Iteration | Result | Observation date |
|---|---|---|
| 1 | Chromium rejected file URL and loopback HTTP navigation with ERR_BLOCKED_BY_ADMINISTRATOR; lane narrowed to loading the package HTML fixture via Playwright `set_content`. Navigation remains untested. | UNKNOWN |
| 2 | First desktop screenshot captured an in-progress reset interpolation; test now waits for the computed transform to settle before asserting and capturing. | UNKNOWN |
| 3 | Playwright `wait_for_function` conflicted with the page CSP; page policy retained, test uses bounded external polling of the existing element's computed transform. | UNKNOWN |
| 4 | Container git cloning failed (no external DNS/network); repository claims rest on connector source reads, not a local build. | UNKNOWN |
| 5 | Native Adobe, Blender, Rive and Remotion execution were unavailable; the limitation is carried through docs, backlog and the validation report. | UNKNOWN |
