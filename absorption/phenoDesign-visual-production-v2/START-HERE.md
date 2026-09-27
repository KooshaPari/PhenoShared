# phenoDesign · Visual production v2

This expands the frontend/3D kit into a cross-media authoring, delivery and verification package. It is a **local integration overlay and agent handoff**, not a remotely committed implementation. Browse `index.html` for tools and skills.

## Contents

- `skills/`: 26 new workflows spanning raster, vector, typography, characters, animation, motion/video, generative media, native hosts, spatial work and E2E verification.
- `reference/frontend-3d-agent-kit/`: the complete original kit, including its 18 original skills, one upstream Anthropic skill, procedural trainer asset and web demos. Its evidence is historical and does not qualify this extension.
- `phenoDesign-overlay/`: a new private integration-primitives package and guarded replacements for PR87's Remotion staging, source geometry and timing components.
- `worker-recipes/`: native Illustrator, Photoshop and After Effects authoring canaries, plus Rive instructions. These are worker-side recipes, not a second engine under phenoDesign/engine.
- `scripts/`: environment probe, guarded overlay installer, Illustrator data compiler, media checks and skill activation.
- `examples/`: vector interaction canary, data jobs and source/acceptance examples.
- `resources/`: annotated source catalog and upstream skill acquisition references.
- `docs/`: ownership, actual repository audit, complete workflow and implementation backlog.
- `evidence/`: actual checks and explicitly labeled environment limitations from package preparation.

## Run locally

```sh
python scripts/probe_tools.py
node --test phenoDesign-overlay/packages/visual-production/test/*.test.mjs
python -m unittest discover -s tests -p 'test_*.py'
python scripts/apply_overlay.py --repo /path/to/PhenoDesign
```

## Handoff State

From `AGENT-HANDOFF.md` — the required scope is **all major visual forms**: frontend layout/type, vector illustration, raster/compositing, icons/identity, characters, frame animation, rigged interactive 2D, 2.5D, 3D objects/scenes/materials, procedural graphics, video/audio/captions, diagrams/data stories, editorial/print and spatial delivery. The product must support creation, iteration, export, actual consumption and E2E validation—not only screenshots or a renderer catalog.

**Intent and authority**: PhenoDesign is the coherent design-facing entry point. Reuse its accepted tokens/themes and the partially absorbed journey viewer/recorder/Remotion packages. Complete the user-requested breadth without building a second registry, graphics SDK or scheduler. Where asset-engine currently owns headless execution, expose it through phenoDesign or intentionally migrate ownership with source custody and consumer updates; do not maintain parallel owners. The user's current desired breadth supersedes a stale “tokens only” interpretation.

**Start from actual code**: Inspect current heads and working changes. The inspected snapshot was main `d11733b1525cb97e045dc7f8d67a05df5501f6c1`; PR87 head `6c99a15337505b55f46a9f576465db5e4053b416` on `absorb-phenojourneys-vue`. At inspection the PR was open/unmerged. Read the current migration and exact source before applying the supplied guarded overlay. Retain newer valid fixes.

**Required fixes and acceptance**:
1. Run `scripts/probe_tools.py`, inspect `docs/REPOSITORY-AUDIT.md`, and run overlay dry-run. Resolve missing migration prerequisites rather than recreating packages. Apply reviewed changes in an owned worktree. Preserve tokens/theme/public exports, tests and unrelated work.
2. Run the dependency-free regression suite, then actual workspace typechecks and target tests. Add Remotion to the workspace and align dependencies/lockfile using the locally installed toolchain. Test real SSR rendering; a `.mjs` syntax check is not that test.
3. Qualify the user's installed Illustrator and Photoshop on dedicated native hosts. Start from `worker-recipes/`. Run the create → editable save → close → cold reopen → structural inspection → export → independent pixel inspection journey. Resolve the script/plugin version, file-grant and session adapter gaps. Automate through the existing journey/native worker machinery; no foreground focus theft.
4. Prove one complete vector/raster/3D/motion product story in an actual consuming page. The story must contain real authored sources and useful interaction; it must not be a dashboard of placeholder shapes. The included dial/trainer are plumbing canaries only. Build and critique the final visual quality for the real subject.
5. Expand by capability demand. Use relevant skills, qualify/acquire missing tools through official sources, retain rights/provenance and complete the same E2E loop for each enabled adapter. Rive CLI, Lottie, Remotion, AE, Krita or Blender are choices, not mandatory installations.

Read the dry-run output. Reconcile PR87 and any changed heads first; the installer refuses to pretend absent migration files exist. Apply only on the intended owned worktree:

```sh
python scripts/apply_overlay.py --repo /path/to/PhenoDesign --apply
python scripts/activate_skills.py --repo /path/to/PhenoDesign --harness codex
```

Skill activation is another dry-run by default; add `--apply` after review. Forge uses `--harness forge`. Existing harness policy files are never replaced. Keep this extracted kit in a stable directory: inherited skills receive its actual absolute reference-kit path, so their original scripts and resources remain resolvable. Native recipes are not silently copied into a second render engine. After integration, align Remotion dependency versions and regenerate the actual Bun lockfile on device; no guessed lockfile is included.

## Boundaries

“Workflow coverage” does not mean every application, plugin and target has passed on-device E2E. Read `evidence/VALIDATION.md`. Native Adobe, Blender, Rive and complete Remotion rendering were not executed in this environment. The included technical shapes are canaries, not finished identity or character art. No Adobe binaries, proprietary fonts, purchased assets or credentials are included.

## File Inventory

Per-file delivery status. `complete` = authored and exercised by the recorded checks, or preserved unchanged. `partial` = authored but its acceptance/host execution is unverified, or its integrity record is now stale. `stub` = placeholder only. No file is classified `stub` in this pass. `reference/frontend-3d-agent-kit/` is the complete original v1 kit, preserved and not requalified. `MANIFEST.sha256` is `partial`: the prior deletion of root `AGENT-HANDOFF.md` plus this pass of documentation edits make its hashes drift from the tree.

| file | status |
|---|---|
| `INVENTORY.md` | complete |
| `LICENSE` | complete |
| `MANIFEST.sha256` | partial |
| `START-HERE.md` | complete |
| `THIRD-PARTY-NOTICES.md` | complete |
| `docs/ADOBE-HOSTS.md` | complete |
| `docs/ALL-FORMS.md` | complete |
| `docs/BACKLOG.json` | complete |
| `docs/E2E-CONTRACT.md` | complete |
| `docs/OWNERSHIP.md` | complete |
| `docs/QUALITY-AND-ALTERNATIVES.md` | complete |
| `docs/REMOTION-E2E.md` | complete |
| `docs/REPOSITORY-AUDIT.md` | complete |
| `docs/SOURCING-AND-RIGHTS.md` | complete |
| `evidence/ITERATION-NOTES.md` | complete |
| `evidence/VALIDATION.md` | complete |
| `evidence/browser-checks.json` | complete |
| `evidence/environment.json` | complete |
| `evidence/media-audit.json` | complete |
| `evidence/node-tests.txt` | complete |
| `evidence/python-tests.txt` | complete |
| `evidence/syntax-results.json` | complete |
| `evidence/synthetic-media-canary.mp4` | complete |
| `evidence/test-toolchain.json` | complete |
| `evidence/vector-desktop.png` | complete |
| `evidence/vector-mobile.png` | complete |
| `evidence/vector-no-js.png` | complete |
| `examples/illustrator.job.json` | partial |
| `examples/photoshop.job.json` | partial |
| `examples/production.job.json` | complete |
| `examples/vector-prop/index.html` | partial |
| `index.html` | complete |
| `phenoDesign-overlay/packages/visual-production/README.md` | complete |
| `phenoDesign-overlay/packages/visual-production/package.json` | complete |
| `phenoDesign-overlay/packages/visual-production/src/contracts.mjs` | complete |
| `phenoDesign-overlay/packages/visual-production/src/geometry.d.mts` | complete |
| `phenoDesign-overlay/packages/visual-production/src/geometry.mjs` | complete |
| `phenoDesign-overlay/packages/visual-production/src/index.mjs` | complete |
| `phenoDesign-overlay/packages/visual-production/src/probe-media.mjs` | complete |
| `phenoDesign-overlay/packages/visual-production/src/staging.mjs` | complete |
| `phenoDesign-overlay/packages/visual-production/test/core.test.mjs` | complete |
| `phenoDesign-overlay/remotion/doc-embeds/bin/render.mjs` | partial |
| `phenoDesign-overlay/remotion/doc-embeds/src/DocEmbed.tsx` | partial |
| `phenoDesign-overlay/remotion/doc-embeds/src/components/Highlight.tsx` | partial |
| `phenoDesign-overlay/remotion/doc-embeds/src/components/SceneView.tsx` | partial |
| `phenoDesign-overlay/remotion/doc-embeds/src/schema.ts` | partial |
| `reference/frontend-3d-agent-kit/AGENT-HANDOFF.md` | complete |
| `reference/frontend-3d-agent-kit/AGENTS.md` | complete |
| `reference/frontend-3d-agent-kit/INVENTORY.md` | complete |
| `reference/frontend-3d-agent-kit/LICENSE` | complete |
| `reference/frontend-3d-agent-kit/MANIFEST.sha256` | complete |
| `reference/frontend-3d-agent-kit/START-HERE.md` | complete |
| `reference/frontend-3d-agent-kit/THIRD-PARTY-NOTICES.md` | complete |
| `reference/frontend-3d-agent-kit/assets/asset-manifest.json` | complete |
| `reference/frontend-3d-agent-kit/assets/concept-trainer.glb` | complete |
| `reference/frontend-3d-agent-kit/assets/concept-trainer.json` | complete |
| `reference/frontend-3d-agent-kit/blender/build_product.py` | complete |
| `reference/frontend-3d-agent-kit/contracts/asset.schema.json` | complete |
| `reference/frontend-3d-agent-kit/contracts/design-tokens.json` | complete |
| `reference/frontend-3d-agent-kit/contracts/quality-budget.json` | complete |
| `reference/frontend-3d-agent-kit/contracts/story.json` | complete |
| `reference/frontend-3d-agent-kit/demo-standalone.html` | complete |
| `reference/frontend-3d-agent-kit/demo/index.html` | complete |
| `reference/frontend-3d-agent-kit/demo/mesh-data.js` | complete |
| `reference/frontend-3d-agent-kit/demo/poster.svg` | complete |
| `reference/frontend-3d-agent-kit/demo/software-viewer.js` | complete |
| `reference/frontend-3d-agent-kit/demo/style.css` | complete |
| `reference/frontend-3d-agent-kit/demo/viewer.js` | complete |
| `reference/frontend-3d-agent-kit/evidence/VALIDATION.md` | complete |
| `reference/frontend-3d-agent-kit/evidence/browser-results.json` | complete |
| `reference/frontend-3d-agent-kit/evidence/browser-tests.txt` | complete |
| `reference/frontend-3d-agent-kit/evidence/desktop-exploded.png` | complete |
| `reference/frontend-3d-agent-kit/evidence/desktop-start.png` | complete |
| `reference/frontend-3d-agent-kit/evidence/mobile-no-js.png` | complete |
| `reference/frontend-3d-agent-kit/evidence/mobile-no-renderer.png` | complete |
| `reference/frontend-3d-agent-kit/evidence/mobile-reduced-motion.png` | complete |
| `reference/frontend-3d-agent-kit/evidence/mobile-start.png` | complete |
| `reference/frontend-3d-agent-kit/evidence/schema-results.json` | complete |
| `reference/frontend-3d-agent-kit/evidence/syntax-results.json` | complete |
| `reference/frontend-3d-agent-kit/evidence/unit-tests.txt` | complete |
| `reference/frontend-3d-agent-kit/index.html` | complete |
| `reference/frontend-3d-agent-kit/integrations/three-gsap/README.md` | complete |
| `reference/frontend-3d-agent-kit/integrations/three-gsap/index.html` | complete |
| `reference/frontend-3d-agent-kit/integrations/three-gsap/main.js` | complete |
| `reference/frontend-3d-agent-kit/integrations/three-gsap/package.json` | complete |
| `reference/frontend-3d-agent-kit/integrations/three-gsap/prepare.mjs` | complete |
| `reference/frontend-3d-agent-kit/recipes/2-5d-fallback.md` | complete |
| `reference/frontend-3d-agent-kit/recipes/active-props.md` | complete |
| `reference/frontend-3d-agent-kit/recipes/glass-control.md` | complete |
| `reference/frontend-3d-agent-kit/recipes/sneaker-story.md` | complete |
| `reference/frontend-3d-agent-kit/resources/BLENDER-AUTONOMY.md` | complete |
| `reference/frontend-3d-agent-kit/resources/HARNESS-SETUP.md` | complete |
| `reference/frontend-3d-agent-kit/resources/LOCAL-GENERATION.md` | complete |
| `reference/frontend-3d-agent-kit/resources/MATERIALS-AND-EXPORT.md` | complete |
| `reference/frontend-3d-agent-kit/resources/QUALITY-GATES.md` | complete |
| `reference/frontend-3d-agent-kit/resources/SOURCES.md` | complete |
| `reference/frontend-3d-agent-kit/resources/STACK-CHOICES.md` | complete |
| `reference/frontend-3d-agent-kit/resources/UPSTREAM-SKILLS.md` | complete |
| `reference/frontend-3d-agent-kit/resources/catalog.json` | complete |
| `reference/frontend-3d-agent-kit/scripts/audit_asset.py` | complete |
| `reference/frontend-3d-agent-kit/scripts/build_asset.py` | complete |
| `reference/frontend-3d-agent-kit/scripts/doctor.py` | complete |
| `reference/frontend-3d-agent-kit/scripts/package_demo.py` | complete |
| `reference/frontend-3d-agent-kit/scripts/run_blender.py` | complete |
| `reference/frontend-3d-agent-kit/scripts/sync_skills.py` | complete |
| `reference/frontend-3d-agent-kit/scripts/verify_manifest.py` | complete |
| `reference/frontend-3d-agent-kit/skills/README.md` | complete |
| `reference/frontend-3d-agent-kit/skills/fd3d-art-direction/SKILL.md` | complete |
| `reference/frontend-3d-agent-kit/skills/fd3d-asset-provenance/SKILL.md` | complete |
| `reference/frontend-3d-agent-kit/skills/fd3d-blender-autonomy/SKILL.md` | complete |
| `reference/frontend-3d-agent-kit/skills/fd3d-device-budgets/SKILL.md` | complete |
| `reference/frontend-3d-agent-kit/skills/fd3d-geometry-nodes/SKILL.md` | complete |
| `reference/frontend-3d-agent-kit/skills/fd3d-gltf-delivery/SKILL.md` | complete |
| `reference/frontend-3d-agent-kit/skills/fd3d-harness-integration/SKILL.md` | complete |
| `reference/frontend-3d-agent-kit/skills/fd3d-interactive-props/SKILL.md` | complete |
| `reference/frontend-3d-agent-kit/skills/fd3d-lighting-cameras/SKILL.md` | complete |
| `reference/frontend-3d-agent-kit/skills/fd3d-local-generative-3d/SKILL.md` | complete |
| `reference/frontend-3d-agent-kit/skills/fd3d-material-lookdev/SKILL.md` | complete |
| `reference/frontend-3d-agent-kit/skills/fd3d-medium-selection/SKILL.md` | complete |
| `reference/frontend-3d-agent-kit/skills/fd3d-procedural-products/SKILL.md` | complete |
| `reference/frontend-3d-agent-kit/skills/fd3d-progressive-enhancement/SKILL.md` | complete |
| `reference/frontend-3d-agent-kit/skills/fd3d-react-three-scenes/SKILL.md` | complete |
| `reference/frontend-3d-agent-kit/skills/fd3d-scroll-story/SKILL.md` | complete |
| `reference/frontend-3d-agent-kit/skills/fd3d-shader-effects/SKILL.md` | complete |
| `reference/frontend-3d-agent-kit/skills/fd3d-visual-qa/SKILL.md` | complete |
| `reference/frontend-3d-agent-kit/tests/browser_smoke.py` | complete |
| `reference/frontend-3d-agent-kit/tests/test_kit.py` | complete |
| `reference/frontend-3d-agent-kit/upstream/anthropic/frontend-design/LICENSE.txt` | complete |
| `reference/frontend-3d-agent-kit/upstream/anthropic/frontend-design/PROVENANCE.json` | complete |
| `reference/frontend-3d-agent-kit/upstream/anthropic/frontend-design/SKILL.md` | complete |
| `resources/SOURCES.md` | complete |
| `resources/UPSTREAM-SKILLS.md` | complete |
| `resources/catalog.json` | complete |
| `resources/repository-snapshot.json` | complete |
| `resources/skills-index.json` | complete |
| `scripts/activate_skills.py` | complete |
| `scripts/apply_overlay.py` | complete |
| `scripts/check_syntax.cjs` | complete |
| `scripts/compile_illustrator.py` | complete |
| `scripts/media_audit.py` | complete |
| `scripts/probe_tools.py` | complete |
| `scripts/verify_manifest.py` | complete |
| `skills/pd-after-effects-production/SKILL.md` | complete |
| `skills/pd-asset-acquisition/SKILL.md` | complete |
| `skills/pd-brand-icons/SKILL.md` | complete |
| `skills/pd-character-animation/SKILL.md` | complete |
| `skills/pd-creative-shaders/SKILL.md` | complete |
| `skills/pd-cross-media-journeys/SKILL.md` | complete |
| `skills/pd-data-diagrams/SKILL.md` | complete |
| `skills/pd-editorial-print/SKILL.md` | complete |
| `skills/pd-frame-sprite-animation/SKILL.md` | complete |
| `skills/pd-generative-assets/SKILL.md` | complete |
| `skills/pd-illustrator-vector/SKILL.md` | complete |
| `skills/pd-interactive-2d/SKILL.md` | complete |
| `skills/pd-lottie-delivery/SKILL.md` | complete |
| `skills/pd-material-textures/SKILL.md` | complete |
| `skills/pd-native-host-validation/SKILL.md` | complete |
| `skills/pd-photoshop-raster/SKILL.md` | complete |
| `skills/pd-remotion-production/SKILL.md` | complete |
| `skills/pd-remotion-regressions/SKILL.md` | complete |
| `skills/pd-render-scheduling/SKILL.md` | complete |
| `skills/pd-repository-integration/SKILL.md` | complete |
| `skills/pd-rive-authoring/SKILL.md` | complete |
| `skills/pd-spatial-scenes/SKILL.md` | complete |
| `skills/pd-type-layout/SKILL.md` | complete |
| `skills/pd-video-audio-post/SKILL.md` | complete |
| `skills/pd-visual-critique/SKILL.md` | complete |
| `skills/pd-visual-production/SKILL.md` | complete |
| `tests/README.md` | complete |
| `tests/browser_canary.py` | complete |
| `tests/test_tools.py` | complete |
| `worker-recipes/README.md` | partial |
| `worker-recipes/adobe/illustrator/author.jsx.in` | partial |
| `worker-recipes/adobe/photoshop/index.html` | partial |
| `worker-recipes/adobe/photoshop/main.js` | partial |
| `worker-recipes/adobe/photoshop/manifest.json` | partial |
| `worker-recipes/after-effects/canary.jsx` | partial |
| `worker-recipes/rive/README.md` | partial |
