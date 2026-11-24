# conductor (conductor.build, now "Conductor from Meta")

Source: /Users/kooshapari/CodeProjects/temp/proresearch-20261110/kiro-conductor-cc.md (primary: https://www.conductor.build/docs/, https://www.conductor.build/docs/concepts/workspaces-and-branches, https://www.conductor.build/docs/reference/checks)

## What it is

Conductor is a Mac app ("Conductor from Meta") that orchestrates agent sessions in parallel git worktrees. "Conductor lets you run Claude Code, Codex, Cursor, and OpenCode in parallel. Each task gets its own workspace, branch, files, terminal, diff, and review path." Object model: Project -> Repository -> Workspace (git worktree + branch + running environment + chats + diff + PR state) -> Branch -> Working tree -> Running environment. 1 project contains 1 repository; 1 repository contains many workspaces; 1 workspace maps to 1 branch; branch is "the review and PR unit". Working tree created with git worktrees. Running environment = app, server, watchers, tests, terminal commands inside a workspace.

## Artifact model (exact paths/filenames it writes)

No requirement/spec artifact model. Model is Project -> Repository -> Workspace (git worktree + branch + running environment + chats + diff + PR state), with per-workspace .context (gitignored notes), Repository Settings, checked-in AGENTS.md / CLAUDE.md / skills, harness-native Plan Mode and Codex goals. Conductor orchestrates git worktrees + agent sessions. Workspaces usually under ~/conductor/workspaces/<repo name>/<workspace name>. Shared: git history, refs, remotes, object database. Gitignored local files (.env.local, local certificates) not carried over automatically - Conductor uses .worktreeinclude-style patterns to copy only files Git already ignores, and setup scripts for dependency install / code generation / DB setup. Two explicit statements: "Workspace isolation is development isolation, not a security boundary. Agents and commands still run on your Mac with your user permissions." "Agents in the same workspace can edit the same files" (deliberate trade-off of running multiple agents in one workspace on one branch).

## Traceability enforcement

NO for requirements; partial for merge readiness. Conductor has no requirement artifact model in its documentation; it delegates planning to the harness (Plan Mode, Codex goals, AGENTS.md/CLAUDE.md/skills) and to chat/.context. Its executable checks are branch/PR-shaped, not requirement-shaped: Checks tab aggregates git status, PR metadata, CI/status checks, deployments, comments, todos; may block/discourage merge on unresolved todos or failed checks. There is no documented artifact tying a CI result or todo back to a requirement. Plan Mode: "asks the agent to make a plan before editing files" - supported for Claude Code and Codex, not supported for Cursor or OpenCode. "For durable project guidance, use Repository Settings or checked-in instruction files (AGENTS.md, CLAUDE.md, or skills)." "For task-specific context, use the chat, attachments, and .context." Codex sessions can set a goal: "a standing objective that Codex keeps pursuing across turns" (/goal), with status and token budget (Codex-native, surfaced by Conductor). Skills supported for Codex, Claude Code, OpenCode (harness's own mechanism, reused). Review loop is PR-shaped (diff -> comments -> checks -> merge), not requirement-shaped. Unit of delegation is the workspace; unit of integration is the branch and pull request. Conductor may block or discourage merge actions when required work is still open, such as unresolved todos or failed checks.

## Interface surface

Mac app (closed/partially-closed). Agent integrations: Claude Code, Codex, Cursor, OpenCode. Plan Mode (Claude Code, Codex only). Codex goals (/goal). Skills (Codex, Claude Code, OpenCode). No CLI/MCP/SDK documented. Todos page (https://www.conductor.build/docs/concepts/todos) returned HTTP 404 - todo item data model and whether it can carry a requirement reference is UNKNOWN. https://www.conductor.build/docs/specs/tasks/ also 404. site:kiro.dev websearch blocked by anti-bot challenge.

## Interactivity

Interactive multi-agent sessions in workspaces. Plan Mode asks agent to plan before editing files (Claude Code, Codex). Codex goals standing objective across turns.

## External verification

Branch/PR-shaped only. Checks tab aggregates git status, PR metadata, CI/status checks, deployments, comments, todos; may block/discourage merge on unresolved todos or failed checks. Diff Viewer + inline comments + agent review. Explicitly "development isolation, not a security boundary". No requirement -> check linkage documented.

## License

UNKNOWN (not stated in draft).

## Notes

Conductor has no requirement artifact model; delegates planning to harness. Its executable checks are branch/PR-shaped, not requirement-shaped. Todos page and specs/tasks page are UNREACHABLE (HTTP 404). A practical consequence: chaining Kiro-style EARS requirements to Conductor workspaces requires the agent itself to carry the requirement text across the boundary - Conductor provides no native field for it.
