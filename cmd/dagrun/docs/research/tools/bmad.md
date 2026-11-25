# bmad (bmad-code-org/BMAD-METHOD)

Source: /Users/kooshapari/CodeProjects/temp/proresearch-20261110/bmad-gsd.md (primary: https://github.com/bmad-code-org/BMAD-METHOD)

## What it is

BMAD-METHOD is a prompt/skill pack plus deterministic Python helper scripts. No daemon, no persistent runtime state of its own. Install via npx bmad-method install (v6.12) or npx skills add bmad-code-org/BMAD-METHOD --skill '*' (v7); some v7 skills shell out to uv run {project-root}/_bmad/scripts/render_skill.py. Artifacts are markdown on disk under the project. Canonical repo bmad-code-org/BMAD-METHOD, archived: false. License MIT (file text "MIT License / Copyright (c) 2025 BMad Code, LLC"; GitHub spdx_id reports NOASSERTION). Stable v6.12, latest release v6.12.4 (2026-10-14); V7 in preview alpha on main, ETA mid-November 2026. Also distributed via Claude Code plugin marketplace (bmad-code-org/bmad-plugins), Codex plugin marketplace, needs uv + Python 3.10+.

## Artifact model (exact paths/filenames it writes)

- Brief - src/bmm-skills/plan/bmad-product-brief/assets/brief-template.md
- PRD - src/bmm-skills/plan/bmad-prd/assets/prd-template.md (with prd-validation-checklist.md, validation-report-template.html)
- Architecture - src/bmm-skills/plan/bmad-architecture/ produces ARCHITECTURE-SPINE.md from assets/spine-template.md; carries numbered decision IDs AD-n, each with Binds / Prevents / Rule fields, plus ## Stack table with version-pinned rows.
- Epics - src/bmm-skills/plan/bmad-create-epics-and-stories/templates/epics-template.md -> epics.md. Frontmatter status: draft / stepsCompleted: [] / inputDocuments: []. Body carries Requirements Inventory (Functional, NonFunctional, Additional, UX Design requirements), FR Coverage Map slot, Epic List.
- Stories - src/bmm-skills/v6-shims/bmad-create-story/template.md (v6) and v6.12 stories.yaml produced by Story Breakdown, schema at src/bmm-skills/plan/bmad-spec/assets/stories-schema.md.
- Tasks - inside the story file (## Tasks / Subtasks), each task annotated with the acceptance criterion it satisfies (- [ ] Task 1 (AC: #)).
- Tracking - src/bmm-skills/plan/bmad-sprint-planning/sprint-status-template.yaml.
- Sharding - bmad-shard-pro skill: trigger past about 50 KB (roughly 8,000 words); three outcomes (leave it / split / contents list); lossless cut with map in main file; original frozen at .source/<name>.md; layout prd-billing/prd-billing.md (main), pricing-and-plans.md, invoicing.md, identifier-lookup.md, .source/prd-billing.md; executable check uv run <skills-folder>/bmad-shard-pro/scripts/shard_tool.py check <folder> --all.

## Traceability enforcement

Chain is statically traceable; nothing re-checks it. epics.md carries "FR Coverage Map" slot and Requirements Inventory (FR / NFR / Additional / UX-DR), and each story task annotated (AC: #) back to story acceptance criteria. But FR Coverage Map is a template slot rendered once at epic-breakdown time ({{requirements_coverage_map}}); nothing re-derives it when PRD changes; PRD, epics doc, story files are separate markdown with no machine link. lint_spine.py validates architecture spine internal consistency (placeholders, AD ids, Binds/Prevents/Rule, Stack version pins) only - says nothing about requirement coverage or tests. bmad-loop runs project's own [verify] commands but checks: spec status, baseline commit, code changed, board matches; never checks commands still cover edited requirement. A spec change invalidating coverage is not detected.

## Interface surface

CLI: npx bmad-method install (v6.12) or npx skills add bmad-code-org/BMAD-METHOD --skill '*' (v7). Skills CLI, Claude Code plugin marketplace (bmad-code-org/bmad-plugins), Codex plugin marketplace. v6.12 src/bmm-skills/agents/ has exactly five personas: bmad-agent-analyst, bmad-agent-architect, bmad-agent-dev, bmad-agent-pm, bmad-agent-ux-designer. v7 preview adds bmad-agent-po (six). Full v7 skill surface is 32 skills. No SM (scrum master) persona - SM job done by skills (bmad-sprint-planning, bmad-create-epics-and-stories). No QA persona in core - QA appears as skill bmad-qa-generate-e2e-tests; enterprise testing is separate module repo bmad-code-org/bmad-method-test-architecture-enterprise. No MCP server and no SDK documented.

## Interactivity

Multi-turn with explicit human gates. Architecture reviewer gate: rubric walker plus every entry in {workflow.finalize_reviewers} run as parallel subagents against ARCHITECTURE-SPINE.md; "independent context is the point". Epic/story creation: "NEVER generate content without user input", "YOU ARE A FACILITATOR, not a content generator". Sharding waits for agreement before changing anything. Headless mode alternative: bmad-prd/references/headless.md says "Do not ask... Do not greet", records assumptions[] and open_questions[] in JSON status, status in {complete, partial, blocked}. Agent-automatic: bmad-build (v7) "Implements a story, feature, or bug fix end to end: plan, code, review, verify" with routes oneshot/full and review none/quick/thorough; bmad-build-auto, bmad-code-review, bmad-review, bmad-retrospective, bmad-eval; deterministic scripts.

## External verification

Thin, mostly outside core repo. Inside core: lint_spine.py (mechanical half of spine decision-integrity; reports JSON findings for placeholder, ad_id, ad_fields, version_pin; exit code always 0, findings travel in JSON; caller decides). shard_tool.py check --all (sharded-document map/frontmatter invariant). prd-validation-checklist.md is judgement, not executable. lint_spine.py has its own test suite (src/bmm-skills/plan/bmad-architecture/scripts/tests/test_lint_spine.py). Real executable verification loop lives in separate repo bmad-code-org/bmad-loop (MIT, early open beta): plain Python drives pick story -> implement -> adversarially review -> verify -> commit; no LLM in control loop; trust nothing, verify everything (spec status, baseline commit, code changed, board matches, then runs your [verify] commands); fresh-context review; one board writer; resumable on-disk state; CRITICAL escalation pauses for bmad-loop resolve; parks human work until bmad-loop confirm. Requires Python 3.11+, tmux 3.2+, BMAD project (v6 >= 6.10.0 with bmad-build-auto, or v7 6.13.0-next).

## License

MIT.

## Notes

Agent personas analyst/PM/architect/dev exist; no SM persona and no QA persona in core (QA is a skill). Only anti-gaming-adjacent checks are placeholder detection and shard map/frontmatter invariant; semantic judgment delegated to independent LLM reviewers. docs/reference/workflow-map.md at ref V6.12 is UNREACHABLE (path does not exist at that ref; only docs/{cs,fr,ko-kr,vi-vn,zh-cn}/reference/workflow-map.md). Artifact chain reconstructed from skill/template files, not from workflow map.
