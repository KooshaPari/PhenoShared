# Source catalog

Reviewed 15 September 2026. **Read** means documentation/source inspection, not installed runtime certification. **Indexed/partial** and **fetch-failed** are deliberately retained rather than falsely called verified. Only R01 is redistributed. Other entries are links with original annotations.

## R01 — Anthropic frontend-design

https://github.com/anthropics/skills/tree/main/skills/frontend-design

Baseline art-direction and design critique; a literal snapshot is included.

**Caveat:** Do not let a generic aesthetic rule override the specific product brief.

**Evidence:** source-and-license-read. **Rights note:** Apache-2.0 for the included skill.

## R02 — Impeccable

https://github.com/pbakaus/impeccable

Opinionated craft, critique and deterministic frontend design audit tooling.

**Caveat:** The reviewed README describes one skill, 24 commands and 61 detector rules. Launcher can download a native engine; review/pin, do not treat as passive text only.

**Evidence:** primary-readme-read. **Rights note:** Apache-2.0; preserve NOTICE when acquiring.

## R03 — Vercel agent-skills

https://github.com/vercel-labs/agent-skills

React architecture/performance, web guidelines and composition patterns.

**Caveat:** Select relevant skills; deployment tools are not authorized by this collection. Resolve complete dependent files and per-skill terms.

**Evidence:** primary-readme-read. **Rights note:** README license claim; inspect exact selected tree before vendoring.

## R04 — CloudAI-X Three.js skills

https://github.com/CloudAI-X/threejs-skills

Ten topic-specific Three.js skill references for geometry, lighting, materials, loaders and interactions.

**Caveat:** Reviewed README install example points at a different repository. License was claimed as MIT but a discrete license file was not established. Reference-only here; do not blindly copy its installer.

**Evidence:** primary-readme-read. **Rights note:** MIT claimed in README; redistribution not independently cleared here.

## R05 — Blender command-line manual

https://docs.blender.org/manual/en/4.5/advanced/command_line/arguments.html

Headless Python jobs, explicit process arguments and failure exit codes.

**Caveat:** Full document fetch failed in this research environment; indexed command documentation was available. Probe installed version and options.

**Evidence:** indexed-partial. **Rights note:** Documentation reference; no manual mirrored.

## R06 — Blender glTF import/export manual

https://docs.blender.org/manual/en/4.5/addons/import_export/scene_gltf2.html

Native-to-browser material/export constraints and supported glTF features.

**Caveat:** Full fetch unavailable; canonical manual link plus partial index only. Test the installed exporter.

**Evidence:** indexed-partial. **Rights note:** Documentation reference.

## R07 — Community MCP for Blender

https://github.com/ahujasid/blender-mcp

Optional live scene inspection/manipulation bridge.

**Caveat:** Third party, not Blender Foundation. Arbitrary Python execution and telemetry enabled by default. Hosted generation integrations are not offline.

**Evidence:** primary-readme-read. **Rights note:** MIT repository plus separate terms/telemetry disclosures; review selected revision.

## R08 — Three.js documentation

https://threejs.org/docs/

Primary renderer, loaders, materials, cameras and WebGPU/TSL API reference.

**Caveat:** Use documentation matching the exact installed release; a dev branch version is not evidence of an npm stable release.

**Evidence:** primary-docs-read. **Rights note:** Three.js software MIT; consult upstream source.

## R09 — React Three Fiber scaling performance

https://github.com/pmndrs/react-three-fiber/blob/master/docs/advanced/scaling-performance.mdx

On-demand rendering, reuse, instancing and React scene performance.

**Caveat:** Demand loops still need invalidation while a spring or control settles. React is not a prerequisite for 3D.

**Evidence:** primary-source-read. **Rights note:** Repository terms apply; reference only.

## R10 — GSAP ScrollTrigger

https://gsap.com/docs/v3/Plugins/ScrollTrigger/

Complex synchronized scroll progress, pinned sections and timeline control.

**Caveat:** Use one transform owner and teardown cleanly; respect current GSAP license.

**Evidence:** primary-docs-read. **Rights note:** GSAP custom standard license; NOT MIT.

## R11 — Motion scroll

https://motion.dev/docs/scroll

A lean alternative for scroll-linked DOM and JS progress callbacks.

**Caveat:** Separate free/public runtime APIs from paid Motion+ resources; do not bundle a paid AI kit.

**Evidence:** primary-docs-read. **Rights note:** Runtime/source and paid resources have distinct terms.

## R12 — CSS animation-timeline

https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/animation-timeline

Native scroll/view timelines for DOM/SVG effects where supported.

**Caveat:** Feature-detect and retain baseline content; not a replacement for the 3D renderer.

**Evidence:** primary-platform-reference-read. **Rights note:** Documentation reference.

## R13 — Lenis

https://github.com/darkroomengineering/lenis

Optional smooth-scroll orchestration when native scrolling demonstrably needs it.

**Caveat:** Not the default. Do not install a second competing RAF or break touch/reduced-motion behavior.

**Evidence:** primary-readme-read. **Rights note:** Check exact revision license before embedding.

## R14 — model-viewer

https://modelviewer.dev/

Simpler product viewing, posters, camera controls and supported AR paths.

**Caveat:** Use before building a custom scene when the interaction is just product inspection.

**Evidence:** primary-docs-read. **Rights note:** Apache-2.0 software; asset rights separate.

## R15 — Rive web runtime

https://rive.app/docs/runtimes/web/web-js

Vector/state-machine active illustrations, controls and meaningful input-driven motion.

**Caveat:** Editable .riv authoring and runtime are different concerns; file and editor rights need review.

**Evidence:** primary-docs-read. **Rights note:** Runtime/editor/content terms distinct.

## R16 — glTF Transform CLI

https://gltf-transform.dev/cli

Inspect and optimize glTF assets through explicit transformations.

**Caveat:** Do not run arbitrary flatten/join/prune recipes that delete nodes needed by interactions.

**Evidence:** primary-docs-read. **Rights note:** MIT software; consult exact dependency lock.

## R17 — Khronos glTF Validator

https://github.com/KhronosGroup/glTF-Validator

Independent standards validation of delivered glTF/GLB.

**Caveat:** The kit Python audit is narrower and is not a substitute.

**Evidence:** primary-readme-read. **Rights note:** Apache-2.0 software.

## R18 — F3D

https://github.com/f3d-app/f3d

Independent local asset inspection and supported screenshot workflows.

**Caveat:** Verify formats/render backend on the actual worker; do not equate successful import with artistic quality.

**Evidence:** primary-readme-read. **Rights note:** BSD-3-Clause software; dependencies vary.

## R19 — Poly Haven asset license

https://polyhaven.com/license

HDRIs, textures and models for local look development with asset provenance.

**Caveat:** CC0 asset licensing does not grant trademark rights or relicense all site code/content. Nothing downloaded automatically.

**Evidence:** primary-license-read. **Rights note:** CC0 assets under published asset policy.

## R20 — ambientCG

https://ambientcg.com/license

Alternative PBR material library for an approved local texture cache.

**Caveat:** The license page could not be fetched during this run. Recheck the actual item and license before download/use.

**Evidence:** fetch-failed. **Rights note:** Unverified in this run; no assets bundled.

## R21 — React Three Rapier

https://github.com/pmndrs/react-three-rapier

Physics for genuinely manipulable objects and collisions.

**Caveat:** Avoid a physics dependency for an ordinary deterministic scroll orbit.

**Evidence:** primary-readme-read. **Rights note:** Check exact release license and dependencies.

## R22 — Playwright visual comparisons

https://playwright.dev/docs/test-snapshots

Browser screenshots and reproducible interaction checks.

**Caveat:** Use stable viewport/state and readiness assertions; image diffs alone are not semantic correctness.

**Evidence:** primary-docs-read. **Rights note:** Apache-2.0 software; docs referenced.

## R23 — Hunyuan3D-2.1

https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1

Optional local image-to-3D shape and PBR texture generation.

**Caveat:** Published VRAM: 10 GB shape, 21 GB texture, 29 GB combined. Hardware/backend/build compatibility must be verified.

**Evidence:** primary-readme-read. **Rights note:** Custom code/weight/model terms require review; not blanket MIT.

## R24 — TRELLIS.2

https://github.com/microsoft/TRELLIS.2

Optional high-capacity local image-to-3D workflow.

**Caveat:** Primary model card lists Linux-tested NVIDIA >=24 GB. Not a promise of Apple Metal support or foreground-coexistence.

**Evidence:** primary-readme-and-model-card-read. **Rights note:** MIT shown for repository; verify weights/dependency terms separately.

## R25 — Agent Skills specification

https://agentskills.io/specification

Interoperable SKILL.md metadata and progressive loading.

**Caveat:** A format standard does not install tools or make untrusted instructions safe.

**Evidence:** primary-spec-read. **Rights note:** Specification reference.

## R26 — Codex skills documentation

https://learn.chatgpt.com/docs/build-skills

Project/shared skill discovery and duplicate-name behavior.

**Caveat:** Use upstream documentation only as a starting point for the user's forks; verify installed discovery.

**Evidence:** primary-docs-read. **Rights note:** Official OpenAI documentation reference.

## R27 — ForgeCode skills documentation

https://forgecode.dev/docs/skills/

Project .forge/skills and shared skill discovery.

**Caveat:** Verify actual local fork and permissions; do not overwrite existing configuration.

**Evidence:** primary-docs-read. **Rights note:** Official project documentation reference.

## R28 — Blender Lab MCP server

https://www.blender.org/lab/mcp-server/

Official Blender Lab experimental MCP direction, distinct from community integrations.

**Caveat:** Indexed primary page available; full fetch failed. Installation/protocol not runtime verified here. Arbitrary-code risks still apply.

**Evidence:** indexed-partial. **Rights note:** Inspect official add-on distribution terms.

## R29 — UI UX Pro Max

https://github.com/nextlevelbuilder/ui-ux-pro-max-skill

Broad style/pattern exploration as an optional source of alternatives.

**Caveat:** Do not treat a large palette/style database as a 3D authoring or visual quality guarantee.

**Evidence:** primary-readme-read. **Rights note:** Review exact selected revision license before collecting files.

## R30 — Anthropic webapp-testing

https://github.com/anthropics/skills/tree/main/skills/webapp-testing

External Playwright workflow reference.

**Caveat:** Not bundled. It references helper scripts; fetching only SKILL.md is incomplete. Its blanket networkidle guidance is not suitable for every continuously connected app; use application readiness.

**Evidence:** source-read. **Rights note:** Inspect per-skill license and complete dependency files.

## R31 — Codrops Creative Hub

https://tympanus.net/codrops/hub/

Find first-party creative studios and implementation references.

**Caveat:** Reference composition and behavior, not unauthorized copying of artwork.

**Evidence:** primary-index-seen. **Rights note:** Item-specific article/demo/code rights.

## R32 — Codrops cinematic 3D scroll tutorial

https://tympanus.net/codrops/2025/11/19/how-to-build-cinematic-3d-scroll-experiences-with-gsap/

A relevant worked example of cinematic 3D scroll composition.

**Caveat:** Title/date indexed from creator site; article fetch timed out. Inspect code and rights before reuse.

**Evidence:** indexed-partial. **Rights note:** Article/demo-specific rights; not mirrored.

## R33 — Codrops scroll tutorial index

https://tympanus.net/codrops/tag/scroll/

A discoverable set of scroll-linked design experiments.

**Caveat:** A visual inspiration index is not an endorsement of every implementation or license.

**Evidence:** primary-index-seen. **Rights note:** Item-specific rights.

## R34 — GSAP standard license

https://gsap.com/community/standard-license/

Current license reference for GSAP use and redistribution.

**Caveat:** Free availability should not be paraphrased as no license restrictions.

**Evidence:** primary-license-read. **Rights note:** Custom GSAP license.

## R35 — TRELLIS.2 model card

https://huggingface.co/microsoft/TRELLIS.2-4B

Primary model requirements and usage context.

**Caveat:** Read model card and associated license before acquiring multi-GB weights.

**Evidence:** primary-model-card-indexed. **Rights note:** Model-specific terms; verify exact revision.

## R36 — Blender Python API export operators

https://docs.blender.org/api/current/bpy.ops.export_scene.html

Exact installed exporter operator and argument documentation.

**Caveat:** Full web fetch failed; probe local operator RNA before accepting an unfamiliar export flag.

**Evidence:** fetch-failed. **Rights note:** Documentation reference.
