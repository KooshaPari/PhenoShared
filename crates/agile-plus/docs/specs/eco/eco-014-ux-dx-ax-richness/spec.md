---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
slug: eco-014-ux-dx-ax-richness
spec_id: eco-014
state: PENDING
status: active
superseded_by: null
title: UX/DX/AX Richness
type: operational
---
# UX/DX/AX Richness

## Problem

User-facing apps across the Phenotype org (web, iOS, desktop, CLI) ship without
a consistent documentation standard for three audiences: human end-users (UX),
contributing developers (DX), and downstream agents/automation (AX). The result
is a "thin app" smell: flows are missing, ergonomics are undocumented, and agent
surfaces (programmatic CLIs, MCP, JSON outputs, structured errors) are
discoverable only by reading source. Reviewers cannot audit richness, and new
contributors cannot onboard from the repo alone.

## Target Users

- **App maintainers** who need a checklist of what to ship in the docs/ tree.
- **Code reviewers** who need an objective acceptance signal.
- **Agents/automation** that consume documented AX surfaces programmatically.
- **End-users** who benefit from richer UX flows captured as diagrams + text.

## Functional Requirements

### FR-1 — `docs/ux.md` (User Experience)
Every public user-facing app MUST ship `docs/ux.md` covering:
1. Primary user journeys (numbered list, each with goal / pre / steps / post).
2. Mermaid diagram of the happy-path flow.
3. Empty, loading, error, and success states for each top-level screen.
4. Keyboard / accessibility affordances summary (focus order, ARIA roles, voice labels for iOS).
5. Dark/light mode behavior where applicable.

### FR-2 — `docs/dx.md` (Developer Experience)
Every public app MUST ship `docs/dx.md` covering:
1. Local dev bring-up (commands, ports, env vars, seeded data).
2. Build, test, lint entry points with one-line descriptions.
3. Code map (key files/folders and their responsibility, ≤12 lines each).
4. Common tasks cookbook (add a route, add a screen, add a CLI subcommand) with diffs.
5. Troubleshooting matrix: symptom → cause → fix.

### FR-3 — `docs/ax.md` (Agent Experience)
Every public app MUST ship `docs/ax.md` covering:
1. Programmatic surfaces: CLI subcommands, MCP tools, HTTP/JSON, IPC, with stable flags.
2. Output schemas (JSON examples, field types) for each non-trivial surface.
3. Exit codes / error envelope contract.
4. Idempotency, rate-limit, and auth posture.
5. Structured example: one full agent run end-to-end with the resulting artifacts.

### FR-4 — Templates
`AgilePlus/docs/templates/ux.md`, `dx.md`, `ax.md` MUST exist as drop-in templates
specifying required headings, minimum section depth, and a working Mermaid
example. App authors copy the template and fill in; reviewers diff against it.

## Acceptance Criteria

- AC-1: For every public app in the Phenotype org, `docs/ux.md`, `docs/dx.md`, and `docs/ax.md` exist and are non-empty.
- AC-2: Each of the three docs contains all required headings from the corresponding template (no skipped sections).
- AC-3: A review check (`task spec:check eco-014`) reports PASS/FAIL with per-app file lists; CI must be advisory (billing constraint) but `task` must be authoritative.

## Constraints

- New docs only; do not move or rename existing documentation.
- "Public app" = any app surfaced to end-users, contributors, or external agents; library-only crates are exempt.
- Templates must remain plain Markdown (no build step, no proprietary format).
- Honor GitHub Actions billing constraint: checks are local-first; CI is advisory.
