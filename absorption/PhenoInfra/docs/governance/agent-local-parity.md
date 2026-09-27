# Agent Local Parity

- **Status:** Draft
- **Date:** 2026-04-30

## Purpose

Record the shared local surfaces that should be visible across Codex, Claude
Code, Cursor, and ForgeCode-adjacent setups.

## Shared MCP Superset

Target common surface:

- `thegent`
- `codex_apps`
- `workos-docs`
- `messages`
- `desktop-automation`

## Shared Compute-Mesh Skill

Mirrored in all three local agent environments:

- `~/.claude/skills/compute-mesh/SKILL.md`
- `~/.codex/skills/compute-mesh/SKILL.md`
- `~/.cursor/skills/compute-mesh/SKILL.md`

## Notes

- `thegent` and `codex_apps` point at the same local orchestration endpoint.
- `messages` is the CLI-backed Messages bridge.
- `desktop-automation` is the desktop control surface.
- `phenotype-infra` remains the canonical home for compute-mesh topology,
  Tailscale control plane, and SSH/Tailscale runbooks.
- Journey traceability is also part of the shared surface:
  - `docs/governance/journey-traceability-standard.md`
  - hwLedger is the reference shape for `ShotGallery` + `RecordingEmbed`

## Compute Plane Reminder

- 7-node hybrid compute mesh is documented in ADR 0001.
- Home desktop heavy-runner behavior is documented in ADR 0003.
- Tailscale SSH and admin-tag gating are documented in ADR 0004 and the
  runbooks.
