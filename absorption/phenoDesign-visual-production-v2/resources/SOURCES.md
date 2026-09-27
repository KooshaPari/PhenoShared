# Primary resources and acquisition leads

A source/README review is not an installed-runtime test. V1-prefixed entries are inherited from the retained kit; read their prior caveats. Failed/partial/reference-only entries are explicitly marked. No external tools are silently installed.

## A01 · Illustrator native scripting
https://helpx.adobe.com/illustrator/desktop/automate-visualize-data/automate-actions/install-and-run-scripts.html

Local editable vector/artboard authoring and script invocation.

Caveat: Do not assume Illustrator uses Photoshop UXP APIs.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## A02 · Photoshop UXP platform
https://developer.adobe.com/photoshop/uxp/2022/

Official Photoshop extension and scripting surface.

Caveat: Installed application/session compatibility still needs qualification.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## A03 · Photoshop executeAsModal
https://developer.adobe.com/photoshop/uxp/2022/ps-reference/media/executeasmodal

Correct serialized app-state mutation and cancellation.

Caveat: Modal execution changes host interaction; not a headless-service claim.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## A04 · Photoshop batchPlay
https://developer.adobe.com/photoshop/uxp/2022/ps-reference/media/batchplay

Automation beyond convenience DOM operations.

Caveat: Record/test descriptors against the installed host; never accept arbitrary untrusted script commands.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## A05 · Photoshop UXP scripting samples
https://developer.adobe.com/photoshop/uxp/2022/scripting/samples/

Official local filesystem and document scripting examples.

Caveat: File grants, fonts and native session ownership remain explicit.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## A06 · Photoshop document API
https://developer.adobe.com/photoshop/uxp/2022/ps-reference/classes/document

Editable source and export API reference.

Caveat: Reopen/structure/pixel checks must follow API completion.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## A07 · Photoshop UXP scripts
https://developer.adobe.com/photoshop/uxp/2022/ps-reference/media/uxpscripting

Script-file execution path in supported Photoshop.

Caveat: A .psjs script is not a standalone Linux Node process.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## A08 · Krita Python scripting
https://docs.krita.org/en/user_manual/python_scripting/introduction_to_python_scripting.html

Scriptable painting/animation application and exporters.

Caveat: Krita host API is not a generic Python module available without the application.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## A09 · Inkscape command line
https://wiki.inkscape.org/wiki/Using_the_Command_Line

SVG-centric CLI editing/export alternative when Adobe adds unnecessary overhead.

Caveat: Probe installed actions/options; version differences matter.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## A10 · Inkscape actions
https://wiki.inkscape.org/wiki/Action

Discoverable operation vocabulary for reproducible SVG automation.

Caveat: Use the actual executable action list before composing a job.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## A11 · Lottie format documentation
https://lottie.github.io/

Timeline vector interchange reference.

Caveat: Do not conflate JSON with dotLottie packaging or assume all DCC effects transfer.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## A12 · After Effects automated rendering
https://helpx.adobe.com/after-effects/desktop/render-and-export/automate-rendering/automated-rendering-network-rendering.html

Documented aerender and render-worker path.

Caveat: Native authoring and plugins/fonts still need separate qualification.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## M01 · Official Remotion agent skills
https://www.remotion.dev/docs/ai/skills

Official skill acquisition and specialized guidance for Remotion work.

Caveat: Linked for installation under current terms; not an unlicensed vendored copy.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## M02 · Remotion skill repository
https://github.com/remotion-dev/skills

Original repository for Remotion skill discovery.

Caveat: Root listing and package metadata were inspected; no standalone top-level license file was visible in that listing. Do not infer universal redistribution permission.
Review state: repository-root-and-package-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## M03 · Remotion bundler API
https://www.remotion.dev/docs/bundle

Controlled bundle root, public directory and source-to-render packaging.

Caveat: Reuse immutable bundles for production rather than rebundling every job.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## M04 · Remotion renderer API
https://www.remotion.dev/docs/renderer/render-media

Programmatic rendering without shell-string command construction.

Caveat: Explicit browser/dependencies and production process isolation required.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## M05 · Remotion dynamic metadata
https://www.remotion.dev/docs/dynamic-metadata

Calculate actual composition dimensions/duration from inputs.

Caveat: Metadata code and input validation must agree.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## M06 · Remotion configuration
https://www.remotion.dev/docs/config

Documented configuration surface.

Caveat: SSR API calls do not automatically honor config-file settings.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## M07 · Remotion license
https://www.remotion.dev/docs/license

Review applicable use/organization terms before production deployment.

Caveat: Do not label Remotion MIT or assume all commercial uses are free.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Read current official Remotion terms for the actual organization/use case.

## M08 · Remotion license FAQ
https://www.remotion.dev/docs/license/faq

Clarify scope/usage questions against the publisher guidance.

Caveat: Guidance is not a substitute for the actual applicable agreement.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## M09 · FFprobe
https://ffmpeg.org/ffprobe.html

Stream metadata for source/export contracts.

Caveat: Metadata alone does not establish visual quality or correct narration.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## M10 · Motion Canvas
https://motioncanvas.io/docs/

Code-authored vector explanatory animation with timed scene structure.

Caveat: Not a replacement for every traditional editing workflow.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## M11 · Manim Community
https://docs.manim.community/en/stable/

Programmatic diagram/math animation with editable scene code.

Caveat: Validate quantities/equations separately from the rendered animation.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## R01 · Rive CLI overview
https://rive.app/docs/cli/overview

Code-first authoring, generated runtime/editor outputs and CLI workflow.

Caveat: Reviewed docs describe editor sync-back limitations; do not assume full round-trip equivalence.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## R02 · Rive agent guide
https://rive.app/docs/cli/agents

Agent-oriented creation, local schema/docs, verification, inspection and screenshots.

Caveat: Qualify exact installed command syntax and runtime export behavior.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## R03 · Rive runtime state machines
https://rive.app/docs/runtimes/state-machines

Input/state behavior in actual consumers.

Caveat: Canvas behavior needs accessibility-equivalent controls and lifecycle tests.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## R04 · Rive web runtime parameters
https://rive.app/docs/runtimes/web/rive-parameters

Artboard/playback/runtime integration details.

Caveat: Authoring and runtime versions require an actual compatibility canary.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## G01 · OpenUSD introduction
https://openusd.org/release/intro.html

Structured scene composition/interchange for richer production workflows.

Caveat: Do not assume conversion into a delivery format preserves every scene feature.
Review state: primary-docs-read; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## G02 · PixiJS interaction guide
https://pixijs.com/8.x/guides/components/interaction/

Candidate interaction/runtime layer for many animated 2D objects.

Caveat: The official page resolved but returned no readable body here; qualify current API directly.
Review state: official-page-resolved-body-unavailable; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## G03 · ComfyUI workflows
https://docs.comfy.org/development/core-concepts/workflow

Candidate local workflow source for generated image/texture assets.

Caveat: Page fetch failed here; this is a discovery lead, not a verified current API. Inspect custom nodes/model terms.
Review state: reference-only-fetch-failed; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## G04 · p5.js reference
https://p5js.org/reference/

Candidate for code-authored 2D generative art and experiments.

Caveat: Reference-only lead in this revision; qualify current APIs and delivery suitability.
Review state: reference-only; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## G05 · Godot documentation
https://docs.godotengine.org/en/stable/

Candidate when a real interactive scene/game export is needed beyond a web prop.

Caveat: Reference-only lead; do not add an engine when a simpler web runtime suffices.
Review state: reference-only; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## G06 · Aseprite documentation
https://www.aseprite.org/docs/

Candidate sprite/cel source and atlas workflow.

Caveat: Reference-only lead; review licensing and the actual batch-export capabilities.
Review state: reference-only; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## G07 · Adobe InDesign developer resources
https://developer.adobe.com/indesign/

Candidate for complex editorial/layout source rather than stretching Illustrator into every document job.

Caveat: Reference-only lead. The user reported Illustrator/Photoshop, not an installed InDesign entitlement.
Review state: reference-only; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## G08 · FreeCAD documentation
https://www.freecad.org/documentation.php

Candidate for dimensional/parametric hard-surface sources when true CAD constraints matter.

Caveat: Reference-only lead; Blender is still the primary existing 3D route for authored visual assets.
Review state: reference-only; reviewed in this expansion as noted.
Rights: Verify the tool, runtime and asset-specific license separately.

## V1-R01 · Anthropic frontend-design
https://github.com/anthropics/skills/tree/main/skills/frontend-design

Baseline art-direction and design critique; a literal snapshot is included.

Caveat: Do not let a generic aesthetic rule override the specific product brief.
Review state: source-and-license-read; inherited snapshot; not freshly requalified.
Rights: Apache-2.0 for the included skill

## V1-R02 · Impeccable
https://github.com/pbakaus/impeccable

Opinionated craft, critique and deterministic frontend design audit tooling.

Caveat: The reviewed README describes one skill, 24 commands and 61 detector rules. Launcher can download a native engine; review/pin, do not treat as passive text only.
Review state: primary-readme-read; inherited snapshot; not freshly requalified.
Rights: Apache-2.0; preserve NOTICE when acquiring

## V1-R03 · Vercel agent-skills
https://github.com/vercel-labs/agent-skills

React architecture/performance, web guidelines and composition patterns.

Caveat: Select relevant skills; deployment tools are not authorized by this collection. Resolve complete dependent files and per-skill terms.
Review state: primary-readme-read; inherited snapshot; not freshly requalified.
Rights: README license claim; inspect exact selected tree before vendoring

## V1-R04 · CloudAI-X Three.js skills
https://github.com/CloudAI-X/threejs-skills

Ten topic-specific Three.js skill references for geometry, lighting, materials, loaders and interactions.

Caveat: Reviewed README install example points at a different repository. License was claimed as MIT but a discrete license file was not established. Reference-only here; do not blindly copy its installer.
Review state: primary-readme-read; inherited snapshot; not freshly requalified.
Rights: MIT claimed in README; redistribution not independently cleared here

## V1-R05 · Blender command-line manual
https://docs.blender.org/manual/en/4.5/advanced/command_line/arguments.html

Headless Python jobs, explicit process arguments and failure exit codes.

Caveat: Full document fetch failed in this research environment; indexed command documentation was available. Probe installed version and options.
Review state: indexed-partial; inherited snapshot; not freshly requalified.
Rights: Documentation reference; no manual mirrored

## V1-R06 · Blender glTF import/export manual
https://docs.blender.org/manual/en/4.5/addons/import_export/scene_gltf2.html

Native-to-browser material/export constraints and supported glTF features.

Caveat: Full fetch unavailable; canonical manual link plus partial index only. Test the installed exporter.
Review state: indexed-partial; inherited snapshot; not freshly requalified.
Rights: Documentation reference

## V1-R07 · Community MCP for Blender
https://github.com/ahujasid/blender-mcp

Optional live scene inspection/manipulation bridge.

Caveat: Third party, not Blender Foundation. Arbitrary Python execution and telemetry enabled by default. Hosted generation integrations are not offline.
Review state: primary-readme-read; inherited snapshot; not freshly requalified.
Rights: MIT repository plus separate terms/telemetry disclosures; review selected revision

## V1-R08 · Three.js documentation
https://threejs.org/docs/

Primary renderer, loaders, materials, cameras and WebGPU/TSL API reference.

Caveat: Use documentation matching the exact installed release; a dev branch version is not evidence of an npm stable release.
Review state: primary-docs-read; inherited snapshot; not freshly requalified.
Rights: Three.js software MIT; consult upstream source

## V1-R09 · React Three Fiber scaling performance
https://github.com/pmndrs/react-three-fiber/blob/master/docs/advanced/scaling-performance.mdx

On-demand rendering, reuse, instancing and React scene performance.

Caveat: Demand loops still need invalidation while a spring or control settles. React is not a prerequisite for 3D.
Review state: primary-source-read; inherited snapshot; not freshly requalified.
Rights: Repository terms apply; reference only

## V1-R10 · GSAP ScrollTrigger
https://gsap.com/docs/v3/Plugins/ScrollTrigger/

Complex synchronized scroll progress, pinned sections and timeline control.

Caveat: Use one transform owner and teardown cleanly; respect current GSAP license.
Review state: primary-docs-read; inherited snapshot; not freshly requalified.
Rights: GSAP custom standard license; NOT MIT

## V1-R11 · Motion scroll
https://motion.dev/docs/scroll

A lean alternative for scroll-linked DOM and JS progress callbacks.

Caveat: Separate free/public runtime APIs from paid Motion+ resources; do not bundle a paid AI kit.
Review state: primary-docs-read; inherited snapshot; not freshly requalified.
Rights: Runtime/source and paid resources have distinct terms

## V1-R12 · CSS animation-timeline
https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/animation-timeline

Native scroll/view timelines for DOM/SVG effects where supported.

Caveat: Feature-detect and retain baseline content; not a replacement for the 3D renderer.
Review state: primary-platform-reference-read; inherited snapshot; not freshly requalified.
Rights: Documentation reference

## V1-R13 · Lenis
https://github.com/darkroomengineering/lenis

Optional smooth-scroll orchestration when native scrolling demonstrably needs it.

Caveat: Not the default. Do not install a second competing RAF or break touch/reduced-motion behavior.
Review state: primary-readme-read; inherited snapshot; not freshly requalified.
Rights: Check exact revision license before embedding

## V1-R14 · model-viewer
https://modelviewer.dev/

Simpler product viewing, posters, camera controls and supported AR paths.

Caveat: Use before building a custom scene when the interaction is just product inspection.
Review state: primary-docs-read; inherited snapshot; not freshly requalified.
Rights: Apache-2.0 software; asset rights separate

## V1-R15 · Rive web runtime
https://rive.app/docs/runtimes/web/web-js

Vector/state-machine active illustrations, controls and meaningful input-driven motion.

Caveat: Editable .riv authoring and runtime are different concerns; file and editor rights need review.
Review state: primary-docs-read; inherited snapshot; not freshly requalified.
Rights: Runtime/editor/content terms distinct

## V1-R16 · glTF Transform CLI
https://gltf-transform.dev/cli

Inspect and optimize glTF assets through explicit transformations.

Caveat: Do not run arbitrary flatten/join/prune recipes that delete nodes needed by interactions.
Review state: primary-docs-read; inherited snapshot; not freshly requalified.
Rights: MIT software; consult exact dependency lock

## V1-R17 · Khronos glTF Validator
https://github.com/KhronosGroup/glTF-Validator

Independent standards validation of delivered glTF/GLB.

Caveat: The kit Python audit is narrower and is not a substitute.
Review state: primary-readme-read; inherited snapshot; not freshly requalified.
Rights: Apache-2.0 software

## V1-R18 · F3D
https://github.com/f3d-app/f3d

Independent local asset inspection and supported screenshot workflows.

Caveat: Verify formats/render backend on the actual worker; do not equate successful import with artistic quality.
Review state: primary-readme-read; inherited snapshot; not freshly requalified.
Rights: BSD-3-Clause software; dependencies vary

## V1-R19 · Poly Haven asset license
https://polyhaven.com/license

HDRIs, textures and models for local look development with asset provenance.

Caveat: CC0 asset licensing does not grant trademark rights or relicense all site code/content. Nothing downloaded automatically.
Review state: primary-license-read; inherited snapshot; not freshly requalified.
Rights: CC0 assets under published asset policy

## V1-R20 · ambientCG
https://ambientcg.com/license

Alternative PBR material library for an approved local texture cache.

Caveat: The license page could not be fetched during this run. Recheck the actual item and license before download/use.
Review state: fetch-failed; inherited snapshot; not freshly requalified.
Rights: Unverified in this run; no assets bundled

## V1-R21 · React Three Rapier
https://github.com/pmndrs/react-three-rapier

Physics for genuinely manipulable objects and collisions.

Caveat: Avoid a physics dependency for an ordinary deterministic scroll orbit.
Review state: primary-readme-read; inherited snapshot; not freshly requalified.
Rights: Check exact release license and dependencies

## V1-R22 · Playwright visual comparisons
https://playwright.dev/docs/test-snapshots

Browser screenshots and reproducible interaction checks.

Caveat: Use stable viewport/state and readiness assertions; image diffs alone are not semantic correctness.
Review state: primary-docs-read; inherited snapshot; not freshly requalified.
Rights: Apache-2.0 software; docs referenced

## V1-R23 · Hunyuan3D-2.1
https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1

Optional local image-to-3D shape and PBR texture generation.

Caveat: Published VRAM: 10 GB shape, 21 GB texture, 29 GB combined. Hardware/backend/build compatibility must be verified.
Review state: primary-readme-read; inherited snapshot; not freshly requalified.
Rights: Custom code/weight/model terms require review; not blanket MIT

## V1-R24 · TRELLIS.2
https://github.com/microsoft/TRELLIS.2

Optional high-capacity local image-to-3D workflow.

Caveat: Primary model card lists Linux-tested NVIDIA >=24 GB. Not a promise of Apple Metal support or foreground-coexistence.
Review state: primary-readme-and-model-card-read; inherited snapshot; not freshly requalified.
Rights: MIT shown for repository; verify weights/dependency terms separately

## V1-R25 · Agent Skills specification
https://agentskills.io/specification

Interoperable SKILL.md metadata and progressive loading.

Caveat: A format standard does not install tools or make untrusted instructions safe.
Review state: primary-spec-read; inherited snapshot; not freshly requalified.
Rights: Specification reference

## V1-R26 · Codex skills documentation
https://learn.chatgpt.com/docs/build-skills

Project/shared skill discovery and duplicate-name behavior.

Caveat: Use upstream documentation only as a starting point for the user's forks; verify installed discovery.
Review state: primary-docs-read; inherited snapshot; not freshly requalified.
Rights: Official OpenAI documentation reference

## V1-R27 · ForgeCode skills documentation
https://forgecode.dev/docs/skills/

Project .forge/skills and shared skill discovery.

Caveat: Verify actual local fork and permissions; do not overwrite existing configuration.
Review state: primary-docs-read; inherited snapshot; not freshly requalified.
Rights: Official project documentation reference

## V1-R28 · Blender Lab MCP server
https://www.blender.org/lab/mcp-server/

Official Blender Lab experimental MCP direction, distinct from community integrations.

Caveat: Indexed primary page available; full fetch failed. Installation/protocol not runtime verified here. Arbitrary-code risks still apply.
Review state: indexed-partial; inherited snapshot; not freshly requalified.
Rights: Inspect official add-on distribution terms

## V1-R29 · UI UX Pro Max
https://github.com/nextlevelbuilder/ui-ux-pro-max-skill

Broad style/pattern exploration as an optional source of alternatives.

Caveat: Do not treat a large palette/style database as a 3D authoring or visual quality guarantee.
Review state: primary-readme-read; inherited snapshot; not freshly requalified.
Rights: Review exact selected revision license before collecting files

## V1-R30 · Anthropic webapp-testing
https://github.com/anthropics/skills/tree/main/skills/webapp-testing

External Playwright workflow reference.

Caveat: Not bundled. It references helper scripts; fetching only SKILL.md is incomplete. Its blanket networkidle guidance is not suitable for every continuously connected app; use application readiness.
Review state: source-read; inherited snapshot; not freshly requalified.
Rights: Inspect per-skill license and complete dependency files

## V1-R31 · Codrops Creative Hub
https://tympanus.net/codrops/hub/

Find first-party creative studios and implementation references.

Caveat: Reference composition and behavior, not unauthorized copying of artwork.
Review state: primary-index-seen; inherited snapshot; not freshly requalified.
Rights: Item-specific article/demo/code rights

## V1-R32 · Codrops cinematic 3D scroll tutorial
https://tympanus.net/codrops/2025/11/19/how-to-build-cinematic-3d-scroll-experiences-with-gsap/

A relevant worked example of cinematic 3D scroll composition.

Caveat: Title/date indexed from creator site; article fetch timed out. Inspect code and rights before reuse.
Review state: indexed-partial; inherited snapshot; not freshly requalified.
Rights: Article/demo-specific rights; not mirrored

## V1-R33 · Codrops scroll tutorial index
https://tympanus.net/codrops/tag/scroll/

A discoverable set of scroll-linked design experiments.

Caveat: A visual inspiration index is not an endorsement of every implementation or license.
Review state: primary-index-seen; inherited snapshot; not freshly requalified.
Rights: Item-specific rights

## V1-R34 · GSAP standard license
https://gsap.com/community/standard-license/

Current license reference for GSAP use and redistribution.

Caveat: Free availability should not be paraphrased as no license restrictions.
Review state: primary-license-read; inherited snapshot; not freshly requalified.
Rights: Custom GSAP license

## V1-R35 · TRELLIS.2 model card
https://huggingface.co/microsoft/TRELLIS.2-4B

Primary model requirements and usage context.

Caveat: Read model card and associated license before acquiring multi-GB weights.
Review state: primary-model-card-indexed; inherited snapshot; not freshly requalified.
Rights: Model-specific terms; verify exact revision

## V1-R36 · Blender Python API export operators
https://docs.blender.org/api/current/bpy.ops.export_scene.html

Exact installed exporter operator and argument documentation.

Caveat: Full web fetch failed; probe local operator RNA before accepting an unfamiliar export flag.
Review state: fetch-failed; inherited snapshot; not freshly requalified.
Rights: Documentation reference

