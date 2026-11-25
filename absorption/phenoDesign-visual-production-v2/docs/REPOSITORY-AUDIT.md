# Repository-specific findings

Inspected September 15, 2026 through the GitHub connector. These are source/metadata findings, **not** a complete repository build or runtime certification. Refresh before applying.

- Repository: `KooshaPari/PhenoDesign`, public and not archived according to repository metadata.
- Main inspected: `d11733b1525cb97e045dc7f8d67a05df5501f6c1`.
- PR87: `absorb(journeys): migrate Vue components from PhenoJourneys`; **open, unmerged** when inspected.
- Head: `6c99a15337505b55f46a9f576465db5e4053b416`, branch `absorb-phenojourneys-vue`.
- PR carries journey-viewer, playwright-record, journey-playwright and remotion/doc-embeds. Its description routes Rust CLI work to phenotype-tooling PR358; that other PR was not audited here.

## Observed gaps and disposition

| Finding | Exact inspected location | This kit's action | Still required |
|---|---|---|---|
| Shared staging directory recursively deleted; global props file; same-basename collision | remotion/doc-embeds/bin/render.mjs | Replacement uses per-run workspace and content-addressed staging | Run real concurrent SSR jobs on installed toolchain |
| Shell-based npx execution, implicit acquisition/browser assumptions | Same file | Replacement uses direct imported renderer APIs and explicit qualified browser | Install/pin dependencies and qualify browser; broker-level sandbox/timeouts |
| TypeScript interfaces without runtime input validation | src/schema.ts / renderer | Runtime validator for bounded local source specs | Match existing journey converter and error presentation |
| Output dimensions reused as source dimensions | src/DocEmbed.tsx | Per-scene measured dimensions | Actual image/video/crop/rotation qualification |
| Cover crop mapped with independent x/y scaling, not offsets; zoom applied only to media | src/components/SceneView.tsx | Shared centered fit/zoom transform for media and source-space overlays | Render true aspect-ratio/zoom fixtures through Remotion |
| Zoom uses composition duration, not local scene duration | Same file | Explicit per-scene frame duration | Boundary-frame captures in actual runtime |
| Highlight end includes an extra frame; click ripple loops via modulo | src/components/Highlight.tsx | Half-open duration and finite ripple | Render frame-before/start/end/end+1 and verify pixels |
| Root workspace is packages/* only | Root package.json | Guarded installer adds remotion/* | Real dependency resolution/Bun lock update |
| Remotion package lacks direct bundler dependency | remotion/doc-embeds/package.json | Installer adds it at existing Remotion range | Align all packages to one actually installed version; add exact lockfile |
| ARIA fallback writes HTML under an ARIA-like path | packages/playwright-record/src/recorder.ts | Documented backlog; no blind recorder rewrite | Typed format discriminator and viewer/CLI compatibility tests |
| Auto-capture swallows capture failures | Same file, wireAutoCapture | Documented backlog | Failed required capture must prevent verified/accepted verdict |
| Two manifests share relative paths but live at different directory depths | Same file, finalize | Documented backlog | Canonical root resolution for sibling/colocated manifests |
| “verified” filename is written by recorder, not independently established | Same file | Evidence-authority boundary documented | Trusted verification, exact assertions and native/consumer identity |
| Root README still says ARCHIVED while repo is active | README.md / metadata | Recorded, not silently rewritten | Reconcile lifecycle/ownership docs with current intent |
| Render scripts historically moved to asset-engine | engine/README.md; docs/SPINE.md | Worker recipes kept separate, coherent phenoDesign surface proposed | Reuse backend or intentionally migrate once, not duplicate |

## Patch application

`apply_overlay.py` uses expected Git blob hashes for the five replaced Remotion source files and the two package metadata files. Additive files refuse unknown conflicts. It does not force an older revision over newer work. The installer needs the migration files already present; missing files are blockers, not an invitation to fabricate the package.

The replacement is narrower than “all Remotion now fixed.” It does not yet repair the recorder, journey-to-embed converter, viewer consumer compatibility or all rendering details. Those remain explicit tasks in BACKLOG.json. Unknown dependency/runtime behavior is unverified until the receiving agent runs it on the real checkout.

Primary source links are pinned in resources/repository-snapshot.json. PR descriptions indicate intent; the actual code observations above come from fetched files.
