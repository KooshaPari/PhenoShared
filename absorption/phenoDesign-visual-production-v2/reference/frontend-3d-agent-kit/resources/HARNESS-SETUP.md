# Harness setup without configuration damage

## Canonical source

The 18 original skills live in `skills/`. Their root paths are expanded when `scripts/sync_skills.py` copies selected instructions into a project. The full kit remains the canonical resource owner. Keep it at a stable path; a relocated kit requires deliberate resync and conflict reconciliation.

Upstream Codex describes project discovery under `.agents/skills` and shared discovery under the user's `.agents/skills`. Upstream ForgeCode describes `.forge/skills` with shared paths. The user's local Codex/Forgecode forks must be tested; upstream documentation is not proof of their exact discovery behavior. See R25/R26/R27.

## Safe default

The sync command defaults to dry-run, checks every selected destination, refuses conflicting files, rejects symlink destinations and never deletes or writes AGENTS.md. Add `--apply` only for the exact reviewed paths. It intentionally does not overwrite files for updates: compare and reconcile first. Identical copies are skipped.

The script copies only original skills. The Anthropic skill remains under `upstream/` with its license/provenance, preventing silent duplicate-name installation. To install it, manually place the complete folder including the license into the chosen canonical owner after checking for an existing frontend-design skill.

## Suggested task-specific sets

Product hero: art-direction, medium-selection, blender-autonomy, procedural-products, material-lookdev, gltf-delivery, scroll-story, progressive-enhancement, visual-qa.

Interactive dashboard prop: art-direction, medium-selection, interactive-props, material-lookdev, progressive-enhancement, device-budgets.

Existing React integration: react-three-scenes, gltf-delivery, scroll-story, visual-qa. Do not require rewriting an otherwise suitable non-React project.

## MCP boundary

Skills are instructions; MCP is a tool transport; Blender/browser workers execute code. None grants authority to expand access. Install and pin only approved servers in isolated local environments, use absolute executable paths and verify actual registered tools. Merge a reviewed configuration fragment rather than replacing global settings. This kit intentionally ships no active connection configuration or unversioned executable launcher.

Confirm discovery using the installed harness's own listing/help. A created directory is not proof that a running agent loaded the new skill.
