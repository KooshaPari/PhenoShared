# claude-code (subagents + skills, Anthropic official docs)

Source: /Users/kooshapari/CodeProjects/temp/proresearch-20261110/kiro-conductor-cc.md (primary: https://docs.claude.com/en/docs/claude-code/sub-agents, https://docs.claude.com/en/docs/claude-code/skills, https://agentskills.io/specification)

## What it is

Claude Code subagents and skills are instruction packaging, not a spec-driven workflow engine. Subagents are Markdown files with YAML frontmatter (body becomes system prompt); only name and description required. Skills are <name>/SKILL.md with frontmatter plus Markdown body, following the Agent Skills open standard that Claude Code extends with invocation control, subagent execution, dynamic context injection. Subagent frontmatter fields: name, description, tools, disallowedTools, model, permissionMode, maxTurns, autoCompactWindow, skills, mcpServers, hooks, memory, background, omitClaudeMd, effort, isolation, color, initialPrompt, experimental. Unrecognized fields ignored without error. Skill frontmatter (Claude Code): name, description, disable-model-invocation, allowed-tools, context: fork, model. Skill frontmatter (Agent Skills standard): name (required, 1-64 chars, lowercase alphanumeric + hyphens, must match parent dir), description (required, 1-1024 chars, what it does and when to use), license, compatibility (<=500 chars), metadata (string->string map), allowed-tools (space-separated pre-approved tools, experimental). Boolean fields accept yes/no/on/off/1/0 in any case plus true/false. Unrecognized field ignored without error. If YAML does not parse, skill loads with no fields set. If opening --- is not first line, whole file treated as skill content. A .claude/commands/*.md file accepts same fields except name and paths (so paths is skill-level field).

## Artifact model (exact paths/filenames it writes)

- Subagent files: project .claude/agents/*.md (walked up from cwd to repo root; nearest definition wins), user ~/.claude/agents/ (recursive), plugin agents/ (recursive; subfolder becomes part of scoped identifier like my-plugin:review:security), managed-settings .claude/agents/, CLI --agents '<json>' for session-scoped definitions. Files watched live (few seconds); three cases still need restart (first file in new agents dir, --add-dir agents, --disable-slash-commands sessions).
- Skill files: enterprise managed-settings dir; personal ~/.claude/skills/<name>/SKILL.md; project .claude/skills/<name>/SKILL.md; nested <subdir>/.claude/skills/; directories passed with --add-dir; plugin <plugin>/skills/; skills synced from claude.ai account. Project skills load from start directory and every parent up to repo root; skills below start directory load lazily the first time Claude reads or edits a file there. Linked git worktree: Claude Code searches parents only up to worktree root, and on v2.1.277+ falls back to main checkout's project skills. Name-collision precedence documented (enterprise > personal > project; added-directory skills get prefixed name). claude plugin validate <dir> validates an agents directory's frontmatter; Agent Skills project ships skills-ref validate ./my-skill.
- Progressive loading: metadata (~100 tokens: name + description) loaded at startup for all skills; instructions (<5000 tokens recommended) loaded when skill activated; resources (scripts/, references/, assets/) load only when required. Claude Code: skill body loads only when used; once loaded, content stays in context across turns. Dynamic context injection: a !`command` line in body run and output substituted before Claude sees content; @file references attach files.

## Traceability enforcement

NONE that binds a requirement to a check. allowed-tools is a permission grant, not verification (Agent Skills spec calls it "pre-approved tools"; Claude Code says a synced skill's allowed-tools grant goes through normal permission flow and does not apply when org sets allowManagedPermissionRulesOnly). skills-ref validate / claude plugin validate validate artifact format (frontmatter parses, naming conventions), not whether skill's behavior satisfies anything. Claude Code ships bundled /run, /verify, /run-skill-generator skills that launch and drive the app "instead of tests alone", and /verify can record its own recipe as a project skill at .claude/skills/verify/SKILL.md. This is real verification guidance, but model-executed instructions, and /verify is invoked by user (docs say some bundled skills "run only when you invoke them"). Commit-time integration: "When a session starts with a skill named verify or simplify in place, Claude Code's commit instructions tell Claude to run it right before each commit, except for changes to docs or tests." This is a hook from harness into agent's commit routine - still instruction-driven, not a requirement -> check mapping. hooks on a subagent (and global hook system) is the one place where an executable check can be attached to an agent's lifecycle (PreToolUse blocking, PostToolUse formatting) - enforcement, user-authored, not derived from a requirement artifact.

Subagent specifics: name unique, <=256 chars, no : (reserved for plugin-scoped ids). Identity comes only from name field, not filename. description: "When Claude should delegate to this subagent"; Claude uses descriptions to decide delegation. Descriptions occupy context; startup warning when combined descriptions of non-built-in subagents exceed 15,000 tokens. tools / disallowedTools: comma-separated string or YAML list. disallowedTools applies first, then tools resolved against remainder; tool in both removed. model: alias (sonnet, opus, haiku, fable), full model ID, or inherit. Resolution order: per-invocation model param -> frontmatter -> CLAUDE_CODE_SUBAGENT_MODEL -> main conversation model. isolation: worktree runs subagent in temporary git worktree, branched by default from default branch rather than parent session's HEAD; auto-cleaned if no changes. skills preloads skills into subagent context at startup (full content injected). hooks lifecycle hooks scoped to subagent (ignored for plugin subagents).

Inferred: neither subagents nor skills carry any field, schema, or documented mechanism that binds a stated requirement to an executable assertion. Both are context and permission packaging. Closest thing to traceability is the transcript (delegation appears as a tool-call row naming the subagent) and claude --debug logs - both observability of activity, not of requirement satisfaction.

## Interface surface

CLI (claude) with --agents, --add-dir, --disable-slash-commands. Slash commands / skills. Plugin system (claude plugin validate). MCP servers (mcpServers field on subagent). No dedicated SDK documented.

## Interactivity

Interactive by default (chat). Skills load on demand; subagents invoked by model based on description. Bundled /verify user-invoked.

## External verification

None that links a requirement to a check. Permission grants (allowed-tools), format lint (skills-ref validate / claude plugin validate), model-executed guidance (/verify), commit-time instruction hook, user-authored lifecycle hooks. No machine-checked requirement-to-test-to-code graph.

## License

UNKNOWN (not stated in draft).

## Notes

Purely instruction packaging. allowed-tools is permission, not verification. skills-ref validate validates format only. Bundled /verify and commit-time hook are model-executed instructions. Subagent hooks can attach user-authored enforcement, but nothing derives it from a requirement artifact. Transcript and debug logs are observability of activity, not requirement satisfaction.
