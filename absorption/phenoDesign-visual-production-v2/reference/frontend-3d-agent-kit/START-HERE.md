# Frontend / 3D Agent Kit

**Purpose:** give a coding agent the design judgment, editable local asset workflow, interaction architecture and verification loop needed to build ambitious product pages—not merely add a rotating model to a template.

Built 15 September 2026. The reference product is an original unbranded concept trainer. Apple/Nike are descriptions of the requested ambition, not copied artwork, an affiliation or a claim of equivalent production polish.

## Open first

Open `index.html` for a searchable, offline resource catalog and `demo-standalone.html` for the interactive example. The latter has no CDN, npm or network requirement. Its documentation links expect the rest of the ZIP nearby. `demo/index.html` is the editable multi-file version.

If local-file navigation is restricted by your browser, serve only this folder locally:

```bash
python -m http.server --bind 127.0.0.1 8080
```

Then open `http://127.0.0.1:8080/`. Stop the server after use. Do not expose the working folder to the public internet.

## What is actually included

| Area | Contents |
|---|---|
| Agent skills | 18 original `fd3d-*` SKILL.md modules plus one byte-verified upstream Anthropic frontend-design skill and its Apache license |
| Resources | 36 annotated primary-source entries, with selection rationale, caveats, license notes and partial/failed-fetch disclosures |
| Local asset creation | Standard-library procedural trainer generator; an actual GLB, structured mesh source and manifest; headless Blender rebuild/render/export script |
| Working example | Native scroll story, real mesh rotation, layer separation, material accents, drag/keyboard controls, pause, responsive layout and static fallback |
| Production integration | A separate Three.js + GSAP implementation sketch, explicitly dependency-unexecuted here |
| Operating guides | Materials/export, local generation, Blender isolation, harness setup, quality gates, recipes and machine-readable contracts |
| Verification | Asset and installer tests, browser smoke script, real screenshots, validation report and checksum manifest |

The kit does **not** include Blender binaries, npm dependencies, model weights, fonts, branded commercial models, paid course text, or an automatically connected MCP server. Unzipping does not install anything.

## Give your agent this

> Read AGENT-HANDOFF.md. Use the canonical skills selectively. First inspect the current project and probe available local tools. Build one complete product story: editable source → three inspected renders → semantically named GLB → interaction → desktop/mobile/fallback validation. Use the original concept trainer only as a starting specimen. Do not substitute a static screenshot for an interactive feature, or an attractive browser screenshot for a valid editable 3D source. Return a runnable result, source/rights manifest, measurements and honest NOT_RUN/BLOCKED_ENV entries. Do not publish, install third-party code or upload assets without separate authorization.

## Minimal local commands

Run from the extracted kit root. Python 3.10+ is the intended baseline; the included standard-library scripts were exercised on Python 3.13.5. Check the evidence report for exact coverage.

```bash
python scripts/doctor.py
python scripts/audit_asset.py
python -m unittest discover -s tests -p 'test_*.py' -v

# Inspect a proposed Blender job; this does NOT launch Blender.
python scripts/run_blender.py --output build/trainer-v1 --render

# Once the executable/path and script are reviewed, explicitly run it.
python scripts/run_blender.py --blender /absolute/path/to/blender --output build/trainer-v1 --render --run
```

Windows: pass the full path to `blender.exe` in quotes. macOS commonly places the executable inside the Blender application bundle; resolve the installed path rather than assuming it. Use a fresh output directory for every build.

To intentionally regenerate the owned concept outputs:

```bash
python scripts/build_asset.py --overwrite
python scripts/package_demo.py
```

## Add skills to a project without overwriting its rules

```bash
python scripts/sync_skills.py --project /absolute/project --harness codex --skills fd3d-art-direction fd3d-blender-autonomy fd3d-scroll-story fd3d-visual-qa
# Review the dry-run, then repeat with --apply.
```

Use `--harness forge` for `.forge/skills`. Without `--skills`, all 18 original modules are proposed. Conflicts refuse writes; upstream skill installation is deliberately manual. Keep the kit in a stable location because synced copies point back here. See `resources/HARNESS-SETUP.md`.

## Read the verification boundary

`evidence/VALIDATION.md` separates real runtime tests from syntax-only and unexecuted paths. This environment has no Blender and blocks WebGL. Browser interaction/pixels were tested through the included **CPU triangle preview**, not certified as GPU-rendered Three.js or production PBR. The asset is an editable concept seed with visible limitations, not a finished photoreal sneaker.

**Recommended production path:** Blender Python for local source creation → inspected and optimized GLB → Three.js/R3F with one chosen scroll controller → browser/visual/accessibility testing. For simpler work, use CSS/SVG/Rive/model-viewer or a poster instead of forcing 3D everywhere.
