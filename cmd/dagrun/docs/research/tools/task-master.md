# task-master-ai (eyaltoledano/claude-task-master)

## What it is

A task-management system for AI-driven development, usable from any AI chat. It parses PRDs into
a dependency-aware task graph, expands tasks into subtasks, analyses complexity, and tracks status
across sessions and contributors. It is a work-tracking layer, not a spec-driven development
methodology.

- Repo: https://github.com/eyaltoledano/claude-task-master
- npm: `task-master-ai` (npm reports version 0.43.1, license "MIT WITH Commons-Clause"; the repo
  LICENSE file header reads "Task Master License" followed by "MIT License / Copyright (c) 2025 -
  Eyal Toledano, Ralph Khreish", which is why GitHub's SPDX detection returns NOASSERTION)
- Measured 2026-11-11 via GitHub API: 28,345 stars, 2,617 forks, latest GitHub release
  `task-master-ai@0.43.1` (published 2026-03-31), last push 2026-04-28T13:27:12Z.
- Docs: https://tryhamster.com/docs/taskmaster

## Artifact model (exact paths/filenames it writes)

- `.taskmaster/` project directory containing: `config.json`, `state.json`, `tasks/`, `templates/`,
  `reports/`, `docs/`, `loop-progress.txt`, `CLAUDE.md`.
- Per-task Markdown files, written by the `generate` MCP tool ("Generates individual task files").
- Integration/config directories in the repo: `.mcp.json`, `.claude-plugin/`, `.cursor/`,
  `.kiro/`, `.vscode/`, `context/`, `apps/`, `mcp-server/`, `bin/`, `scripts/`.
- Task graph data: task IDs, dependencies, subtasks, tags/workstreams, complexity scores,
  implementation notes appended via `update_subtask`.

## Traceability enforcement (does it bind requirement -> test -> code; enforced or advisory; what breaks the chain)

NONE for requirement -> test -> code. The implemented chain is PRD -> task -> subtask -> notes.

- `parse_prd` "Parses a PRD to generate tasks"; `expand_task`/`expand_all` break a task into
  subtasks; `analyze_project_complexity` scores it.
- Dependencies are first-class and machine-checked: `add_dependency`, `remove_dependency`,
  `validate_dependencies` ("Validates the dependencies of all tasks"), `fix_dependencies` ("Fixes any
  invalid dependencies").
- `update_subtask` "Appends information to a subtask" - this is where implementation evidence
  lands, but it is free text written by the agent.
- There is no requirement-ID entity, no test artifact reference, and no code-link entity. Nothing
  checks that a task has a corresponding test or that a PRD clause is covered by a task.

What breaks the chain: the chain stops at "task marked done". Dependency validation protects graph
integrity, not intent coverage. Any requirement-to-test binding would have to be layered on top of
the task metadata.

## Interface surface (CLI / MCP / SDK / IDE plugin / slash commands)

- MCP server (recommended): `claude mcp add taskmaster-ai -- npx -y task-master-ai`, or the
  Cursor one-click deep link. Built on `fastmcp`; 36 tools total, selectable by
  `TASK_MASTER_TOOLS` (core/lean = 7 tools, standard = 15, all = 36, or a custom comma list).
  The server logs "Successfully registered 15/15 tools" at startup.
- Tool families: task/subtask management, task information and status, analysis and expansion,
  dependency management, project and configuration (`initialize_project`, `generate`, `models`,
  `research`), and tag management.
- CLI commands (docs: `capabilities/cli-root-commands`) and MCP tools reference (docs:
  `capabilities/mcp`) both exist, plus editor integration files for Claude Code, Cursor, Kiro, and
  VS Code.
- AI features (parse PRD, research, complexity analysis) call external models configured via
  `models`; three slots are documented: main model, research model, and fallback model, each needing
  a provider API key unless using Claude Code or Codex CLI OAuth.
- No standalone SDK surface documented.

## Interactivity (multi-turn refine+freeze conversation, or one-shot generate)

Predominantly one-shot generation with agent-driven interaction around it. `parse_prd` is a single
PRD-to-tasks transformation; `expand_task` is a single expansion; `research` is a single AI
research call. The `loop` command automates repeated task execution, and MCP tools are called
ad hoc by an agent during a chat, so refinement happens conversationally through the tool calls
rather than through a built-in multi-turn spec interview.

## External verification (executes/verifies real artifacts, or only checks presence)

Only presence. No test execution, no lint run, no CI gate, no build verification. `generate`
writes task Markdown files; `validate_dependencies` checks graph consistency (a structural check on
the tool's own metadata). The `research` tool gathers external information with AI models but
verifies nothing about the code.

## Autograder fit (could it grade a school-assignment submission: prompt + test + stub + base scope? yes/no + why)

No. Task Master tracks work; it does not grade. It can express a submission workflow - parse the
assignment PRD into tasks, tag the workstream, record subtask notes and status - and the
dependency graph can show whether every planned piece was completed. But there is no rubric, no
test execution, no acceptance-criteria entity, and no scoring, so it cannot decide pass/fail.

## Gaps for our use case

- Context cost: 36 MCP tools; the tool set has to be trimmed by mode to stay usable.
- Requires separate model API keys for the AI features, so a run depends on extra credentials.
- Non-determinism: `parse_prd`, `expand_task`, and `research` are model-generated, so task graphs
  differ between runs for the same PRD.
- State lives in `.taskmaster/` (project files plus `state.json`), so task history is not a git
  object with authorship.
- No link from tasks to tests or code, so completion status is agent-asserted.

## Non-goals (what it deliberately does not do)

- It is not a spec-driven development methodology: no requirements/design/tasks phase model with
  approval gates, and no specification artifact beyond the PRD input.
- It is not a test runner, CI system, or coverage tool.
- It does not verify implementation correctness; status is set by the agent or user.
- It does not replace the AI chat client: "designed to work seamlessly with any AI chat", and the
  MCP server is the integration point.