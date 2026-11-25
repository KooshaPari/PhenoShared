# End-to-end contract: source → artifact → actual experience

## Stage model

| Stage | Minimum retained facts | Real acceptance |
|---|---|---|
| Intent and art direction | Brief, audience, actual content, constraints, chosen/rejected medium, source/token owner | Observable goal and placement-specific quality bar |
| Tool/source qualification | Tool/app/build, permissions, license, source inputs, native session or worker identity | Actual required capability probed, not just an installed icon |
| Authoring | Editable source and recipe, layer/part/state identities, parameters and dependencies | Source exists and can be modified/reproduced |
| Native/source validation | Cold reopen, object/layer/rig/font/link inventory, source renders | Structure and appearance survive reopening |
| Export | Settings, format/profile/alpha/units, dimensions, input/output hashes | Actual bytes decode/parse and meet contract |
| Consumer integration | Exact page/app/build/component and asset paths | Real target loads the actual derivative |
| Behavior | Inputs, state transitions, timings, focus, lifecycle/fallback paths | Required assertions exercise actual user-visible behavior |
| Perceptual review | Placement-size captures, before/after comparison, critique and unresolved limitations | Deliberate accepted visual quality; not a magical score |
| Delivery | Accepted artifacts, version linkage, release and rollback target | Consumer has correct version; publication has separate authorization |

Passing a stage never implies a later stage. A Blender render cannot prove a WebGL page, a Remotion render cannot prove original recorder assertions, and a native API success cannot prove a PSD remains editable after cold reopen.

## Contract extension, not a competing ledger

Keep existing journey IDs and canonical manifest semantics. Attach a namespaced production record containing medium, source refs, recipe/tool identities, output refs/hashes, placement, assertions and raw/presentation relationships. Resolve existing authoritative schema and verifier before merging. The supplied `production.job.json` and JS validators are draft boundary objects to adapt, not a replacement for the ecosystem's canonical manifests.

The suggested adapter capability vocabulary is: probe, author, inspectSource, export, inspectExport, capture, exerciseConsumer, cleanup. These are conceptual operations, not invented claims that every application has those CLI commands. An adapter advertises only implemented, tested operations and reports unsupported ones explicitly.

## Evidence separation

Raw captures and recorded assertions are immutable evidence masters. Annotated, cropped, retimed, narrated, composited or generatively enhanced material is presentation media. Each derivative identifies its parents and transformations. Never patch pixels or metric values into a screenshot to make a failing journey look successful. Hashes verify bytes, not who produced them; bind trust to the existing protected capture/verifier boundary.

Maintain separate facts for transport success, export integrity, semantic assertions, environment readiness and visual acceptance. Do not call a hand-authored manifest “verified” simply because it is named manifest.verified.json. The dependency-free aggregate function combines reported statuses only and is not an independent verifier.

## Verdicts

Use PASS, FAIL, BLOCKED_ENV, BLOCKED_AUTH, INCONCLUSIVE and CANCELLED consistently with the established system. Missing required assertions, capture failure, unrecognized structural format or an untested renderer must not produce PASS. Treat an empty required-check list as incomplete until the contract explicitly says no checks apply; do not exploit vacuous truth to certify an asset.

## Required negative tests

At minimum: missing/truncated asset, off-root/symlink input, wrong source dimensions, wrong duration, muted/missing audio, crop mismatch, stale cache/source version, failed screenshot, unsupported structural snapshot, incorrect keyboard mapping, reduced-motion omission, native modal lock, revoked file token, interrupted render, concurrent staging collision and a deliberately poor/unreadable placement. Retain these failures and prove the apparatus rejects them.

## Privacy and resource custody

Use owned application documents, browser contexts, worktrees and output paths. Capture only the assigned product/app/session. No personal browser profiles, global microphone capture, production secrets or unbounded home mounts. Protect foreground gaming/audio work with small measured render budgets. A native Adobe session is not a hidden Linux worker. Enable expensive tool legs only after real canaries and scheduling limits pass.
