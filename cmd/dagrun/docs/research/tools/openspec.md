# openspec (Fission-AI/OpenSpec)

Source: /Users/kooshapari/CodeProjects/temp/proresearch-20261110/openspec.md (primary: https://github.com/Fission-AI/OpenSpec, https://openspec.dev/docs/cli)

## What it is

A spec-driven-development (SDD) layer aimed at AI coding assistants. Pitch: "fluid, not rigid" - agree on what to build before code exists, but keep every artifact editable at any time, with no phase gates. Installed per project (openspec init), writes a Markdown corpus plus agent instruction files (skills and slash commands) for 30+ assistant integrations. Distributed as standalone binary, npm package (@fission-ai/openspec), Homebrew formula, Nix flake. MIT.

## Artifact model (exact paths/filenames it writes)

- openspec/config.yaml - project config, carries schema: spec-driven (and optionally a store: line).
- openspec/changes/<change-id>/proposal.md - why we are doing this, what changes.
- openspec/changes/<change-id>/specs/ - requirement deltas, per spec id, as specs/<spec-id>/spec.md.
- openspec/changes/<change-id>/design.md - technical approach.
- openspec/changes/<change-id>/tasks.md - implementation checklist; progress counted from - [ ] checkboxes only.
- openspec/specs/<spec-id>/spec.md - durable current requirements (not the delta).
- openspec/changes/archive/<YYYY-MM-DD>-<change-id>/ - frozen change after openspec archive.
- Deltas use fixed headers: ## ADDED|MODIFIED|REMOVED|RENAMED Requirements, then ### Requirement: <name> and inside it #### Scenario: <name> with WHEN/THEN bullets.
- Generated per-tool integration files, e.g. .claude/skills/openspec-<workflow>/SKILL.md and command stubs; equivalent dirs for Cursor, Copilot, Codex (.agents/), etc.

## Traceability enforcement

Requirements are first-class and machine-parseable; openspec validate enforces schema shape: an ADDED requirement with no #### Scenario: block is an ERROR, not a warning; --strict promotes warnings to failures. Real enforcement - but only of spec grammar, not of the gap between spec and tests or code. Nothing in the CLI reads test files, coverage output, or source, so requirement -> test -> code is advisory. Chain breaks when code is written: tasks.md checkboxes can be ticked by the agent without verification; progress is literal checkbox counting (validate warns when a change has zero checkboxes because progress silently reads as "no work"). archive only checks structure and (optionally) incomplete tasks; store-only repos intentionally hold plan artifacts with no code at all.

## Interface surface

CLI primary: init, update, config, list, show, view, validate, archive, status, new, instructions, templates, schemas, doctor, context, store, workset, version, install, completion. Machine output via --json (structured reports, --report findings, --dry-run --json change plans). Agent surface is skills + slash commands: canonical /opsx:propose, plus /opsx:explore, /opsx:apply, /opsx:archive, expanded profile (/opsx:new, /opsx:continue, /opsx:ff, /opsx:verify, /opsx:bulk-archive). No MCP server and no published SDK observed - UNKNOWN.

## Interactivity

Multi-turn, but explicitly not freeze-first. /opsx:explore is a no-stakes thinking partner that reads code and shapes a plan; /opsx:propose then materialises the change folder. After that docs stress "update any artifact anytime, no rigid phase gates" - deliberate opposite of a freeze gate: no locked revision, no signed baseline, no transition refusing further edits. Archiving is closest thing to a freeze, and it is voluntary.

## External verification

Structure only. validate parses deltas and reports ERROR/WARNING/INFO; runs archive merge builder as preflight and surfaces merge conflicts as INFO. Never executes a test, builds code, measures coverage, or inspects whether an implemented file matches its requirement. archive moves the folder and merges deltas into openspec/specs/, nothing more. No anti-gaming detection: a scenario can be vague prose or copied, a task list ticked without work, nothing objects.

## License

MIT.

## Notes

No freeze semantics; validation is grammar not behaviour; no DAG or execution; overlaps AgilePlus change lifecycle so do not re-home its changes/ model into dagrun; checkbox-only task progress is a gaming surface to harden.
