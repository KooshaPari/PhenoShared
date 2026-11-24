# Global Claude Code Instructions

These rules apply to ALL projects. Project-level CLAUDE.md files supplement (and may override) these.

---

# Dependency & Technology Preferences (ENFORCED)

**Bleeding-edge first**: Always prefer the newest stable versions of libraries, frameworks, and tools. When selecting dependencies:
- Use latest major versions, not LTS unless explicitly required
- Prefer cutting-edge CSS/JS/UI tools over mature but stagnant ones
- Check npm/crates.io/pkg.go.dev for latest versions before specifying deps
- Flag any dep that is >1 major version behind latest

**Wrap/Fork/Integrate over Hand-Roll**:
- Before writing any utility, search for an existing OSS library that does it
- Prefer wrapping a well-maintained OSS package over reimplementing
- Fork and extend rather than rewrite from scratch
- Document the wrapped library in comments: `// wraps: <lib-name> <version>`
- Source: dinoforge xDD governance protocols, Phenotype wrap-over-handroll mandate

**Rich UI mandate**:
- All UI work must use a rich component library (Radix, shadcn, Headless UI, etc.)
- No plain HTML forms without a design system
- Prefer: hover-to-expand, progressive disclosure, gallery views, tooltips
- Typography: monospace for technical/code UI elements, system sans for prose
- Dark mode first, light mode as secondary

---

# Prose & Documentation Quality

- Use vale + markdownlint for all documentation
- Embed Mermaid diagrams for architecture flows
- Embed React/MDX widgets in VitePress docsites where appropriate
- Optimize docs for agentic R/W AND human R (no human writes — prompts only)
- Store raw user prompts alongside agent-generated specs

---

## Child-Agent and Delegation Policy

- Use child agents as the default for high-context, multi-file, or parallelizable work.
- Delegate exploration, audits, and long-running analysis to subagents before the parent agent edits.
- Keep parent-agent direct edits narrowly scoped to synthesis, integration, and finalization.

---

# Context Management Strategy

## The Manager Pattern

**CRITICAL**: Operate as a strategic manager, not a worker. Delegate to subagents.

### Keep in Main Context
- User intent and requirements
- Strategic decisions and trade-offs
- Summaries of completed work
- Critical architectural knowledge

### Delegate to Subagents
- File exploration (>3 files)
- Pattern searches across codebase
- Multi-file implementations
- Long command sequences
- Test execution

## Delegation Quick Reference

| Need | Delegate To | Example Prompt |
|------|-------------|----------------|
| Find code patterns | `Explore` | "Find all error handling patterns" |
| Design approach | `Plan` | "Design auth implementation strategy" |
| Run commands | `Bash` | "Run test suite and report failures" |
| Multi-step implementation | `general-purpose` | "Implement and test feature X" |
| Quick isolated fix | DO NOT delegate | Handle directly |

### Parallel vs Sequential

**Parallel** (no dependencies): Launch 2-3 explore agents simultaneously for independent searches.

**Sequential** (dependent): explore -> receive summary -> plan based on findings -> implement approved plan.

## Subagent Swarm (async orchestration)

**If you have subagent/swarm capabilities:** Use them as an **async swarm**.

- **Call task agents async.** Fire tasks so that as each completes, you are reawoken to re-evaluate, spawn more agents, or do more work yourself.
- **Run a swarm.** Up to **50 concurrent task agents**. Scale up when work is well decomposed and independent.
- **Work in between.** While tasks run async, use your own context for planning, monitoring, or other work.
- **Reawaken on completion.** When idle, you will be reawoken as each agent completes. Use that to spawn more agents, do follow-up work, or consolidate results.

## Anti-Patterns

| Bad | Good |
|-----|------|
| Reading 10 files to "understand" | Delegate exploration, get summary |
| Editing files for multi-file changes | Delegate to `general-purpose` |
| Sequential explorations one-by-one | Batch parallel explores |
| Asking subagent for "all results" | Ask for "summary" or "key files" |
| Committing all dirty worktree changes in one commit | Split into targeted, provenance-based commits to preserve local auditability in concurrent-agent environments |

## Dirty-Tree Commit Discipline (Required)

In dirty worktrees, separate commits by provenance:

- `MODE 1`: user-requested implementation changes.
- `MODE 2`: pre-existing work and WIP from other actors.
- `MODE 3`: generated or temporary artifacts (benchmark runs, telemetry snapshots, repair notes).

Never mix modes in one commit. Prefer multiple small commits over one omnibus commit.

## Context Budget Rule

If task adds >2000 tokens of file content/output, **delegate it**.

---

# Optionality and Failure Behavior

**Require** dependencies where they belong; **require** clear, loud failures -- no silent or "graceful" degradation.

- **Force requirement where it belongs.** Do not make dependencies "optional" just to avoid failure. If a service or config is required for correctness, treat it as required and fail when missing.
- **Fail clearly, not silently.** Use explicit failures -- not reduced functionality, logging-only warnings, or hidden errors. Users must see *what* failed and that the process did not silently degrade.
- **Graceful in other ways.** Retries with visible feedback (e.g. "Waiting for X... (2/6)"); error messages that list each failing item; actionable messages and non-obscure stack traces. Do *not* use optionality or silent fallbacks as a substitute for fixing the real dependency.

---

# Planner Agents: No Code in Docs or Plans

**Planner agents** (PM, Analyst, Architect, etc.) must **never write code** in documentation and plans. Their job is to equip implementers. Write specs, acceptance criteria, architecture decisions, and clear handoffs. Prefer references, file paths, or brief pseudocode when necessary.

---

# Phased WBS and Plans with DAGs

When generating **plans**, **roadmaps**, or **implementation breakdowns**:

- **Phases:** Structure into ordered phases (Discovery, Design, Build, Test/Validate, Deploy/Handoff). Each phase contains deliverable-oriented work packages.
- **DAG:** Tasks have explicit **predecessors**; no cycles. List dependencies so execution order is unambiguous.
- **Output:** Phased WBS (hierarchy by phase) plus dependency list or DAG. Optionally: **Phase | Task ID | Description | Depends On** table.

---

# Timescales: Agent-Led, Aggressive Estimates

**Assume an agent-driven environment.** No user or external human intervention beyond prompts.

- **Forbidden in plans:** "Schedule external audit", "Stakeholder Presentation", "Team Kickoff", "Human checkpoint", "Get approval from X", or any step assigning work to a human.
- **Effort in agent terms only:** Agent actions (tool calls, subagent batches). Aggressive wall-clock -- err on the lower bound.
- **Rough mapping:**
  - Trivial change: 1-2 tool calls, <1 min
  - Small feature: 3-6 tool calls, 1-3 min
  - Cross-stack feature: 8-15 tool calls or 2-3 parallel subagents, 3-8 min
  - Major refactor: 15-30 tool calls or 3-5 parallel subagents, 8-20 min
  - Multi-phase initiative: decompose into agent batches; each batch 10-20 min max
- **Forbidden phrasing:** "This will take 2 days", "Schedule a review", "Assign owners", "Present to stakeholders". Use: "N tool calls", "N parallel subagents", "~M min wall clock".

---

# Documentation Organization

**CRITICAL**: All project documentation follows a strict organization structure.

### Root-Level Files (Keep in Root)
- `README.md` -- Main project documentation
- `CHANGELOG.md` -- Project changelog
- `AGENTS.md` -- AI agent instructions
- `CLAUDE.md` -- Claude-specific instructions
- `00_START_HERE.md` -- Getting started guide (if applicable)
- Spec docs: `PRD.md`, `ADR.md`, `FUNCTIONAL_REQUIREMENTS.md`, `PLAN.md`, `USER_JOURNEYS.md`

### Documentation Structure

All other `.md` files must be organized in `docs/` subdirectories:

```
docs/
  guides/              # Implementation guides and how-tos
    quick-start/       # Quick start guides
  reports/             # Completion reports, summaries, status reports
  research/            # Research summaries, indexes, analysis
  reference/           # Quick references, API references, trackers
  checklists/          # Implementation checklists, verification lists
  changes/             # Per-change proposal/design/task docs
    archive/           # Completed change docs
```

### File Organization Rules

1. **Quick Starts** -> `docs/guides/quick-start/` (`*QUICK_START*.md`, `*QUICKSTART*.md`)
2. **Quick References** -> `docs/reference/` (`*QUICK_REFERENCE*.md`, `*QUICK_REF*.md`)
3. **Implementation Guides** -> `docs/guides/` (`*GUIDE*.md`)
4. **Completion Reports** -> `docs/reports/` (`*COMPLETE*.md`, `*SUMMARY*.md`, `*REPORT*.md`, `PHASE_*.md`, `*TEST*.md`)
5. **Research Files** -> `docs/research/` (`*RESEARCH*.md`, `*INDEX*.md`)
6. **Checklists** -> `docs/checklists/` (`*CHECKLIST*.md`)
7. **Trackers** -> `docs/reference/` (`*TRACKER*.md`, `*STATUS*.md`, `*MAP*.md`)

### AI Agent Instructions

- **NEVER** create `.md` files in the project root (except allowed root-level files above)
- **ALWAYS** place new documentation in the appropriate `docs/` subdirectory
- **VERIFY** file location before creating documentation
- **MOVE** misplaced files to correct subdirectories if found

---

# Opinionated Quality Enforcement

- Enforce opinionated styling to a strict degree.
- Programmatic enforcement must guard against bad quality and antipatterns.
- Rather than disables or ignores, fix code properly.
- Use project linters, formatters, and type checkers. Never bypass them.

## Suppression/Ignore Rules (STRICT)

The following are **NOT valid reasons** to suppress, ignore, or bypass any lint, type, or quality check:

- "non-blocking" — all errors must be fixed before considering work complete
- "pre-existing" — all errors must be fixed regardless of who introduced them
- "will fix later" / "deferred" / "TBD" — no deferred quality debt
- "not our code" / "third-party" — own all quality in your PRs

Any suppression MUST include:
1. The specific rule/code being suppressed
2. A concrete justification for WHY it cannot be fixed
3. A tracking reference (ticket/issue URL) for follow-up

Violations of this rule are considered quality policy breaches.

---

# Specification Documentation System

See `~/.claude/references/SPEC_DOCUMENTATION_SYSTEM.md` for complete documentation system specification, including:
- Required project documentation (PRD, ADR, FR, PLAN, USER_JOURNEYS)
- Required tracker documentation (all FR/test/journey trackers)
- Auto-detection behavior for session start
- VitePress docsite setup (greenfield & brownfield)
- Documentation organization rules and file structure
- Change documentation guidelines
- Doc format standards and global reference docs

---

# Generalized Dev Environment Pattern

## Service Management

- **The user runs a dev TUI/dashboard in their own terminal.** This is their primary observation interface. **Never** start, stop, or restart the entire dev stack (`make dev`, `make dev-tui`, `make dev-down`) — only the user does that.
- **Use CLI introspection and per-service manipulation commands** to interact with the running stack without disrupting the user's TUI session. Process orchestrators (e.g. `process-compose`) expose a CLI/API that operates on the same running instance.
- **Assume services use hot reload** (file watchers, HMR, etc.). Save files and let watchers pick up changes — do not restart services just because you edited files.
- **When a service needs restarting** (e.g. config change, dependency update, crash), restart only that specific service via CLI, not the whole stack.
- **Read logs via CLI or log files** — never attach to or interfere with the user's TUI terminal.
- Before starting dev yourself, verify processes are not already up (check health endpoints, status commands, or log files) to avoid duplicate stacks.

## Package Manager

**Use the project's preferred package manager.** Detect from lockfiles:
- `bun.lockb` or `bun.lock` -> use `bun`
- `pnpm-lock.yaml` -> use `pnpm`
- `yarn.lock` -> use `yarn`
- `package-lock.json` -> use `npm`
- If unclear, check `package.json` `packageManager` field or project CLAUDE.md

## Native Over Docker

**Prefer native services over Docker** for local development. Run databases, caches, reverse proxies as native processes. Use Docker only when native install is not feasible or explicitly required.

## OSS and Free First

**Strictly prefer local, OSS, and free tools** over paid SaaS. If a feature requires external services, prefer OSS/self-hosted or free options first. Document paid options only as labeled fallback.

## Multi-Actor Coordination (generalized)

When multiple agents or actors share a dev environment:
- **Debounce commands:** Use project-provided wrappers (Makefile targets, scripts) that prevent concurrent execution conflicts.
- **Shared service management:** Use the project's process orchestrator as source of truth for service health.
- **Hold-if-running logic:** Prefer wrappers that allow multiple actors to share processes without force-killing.
- **Consolidated targets:** Prefer consolidated build/lint/test targets over a multitude of specialized ones.

---

# GitHub Actions & CI Billing Policy

**CRITICAL**: GitHub Actions billing is a hard constraint. No additional funds will be added. The free tier (approx $450) is exhausted instantly by agent swarms (65+ agents).

### Runner & Merge Strategy
- **Skip Billed Runners**: Explicitly skip macOS, Windows, and non-standard large runners in favor of standard Linux runners.
- **Bypass Rule**: If CI fails on billed runners (macOS/Windows) due to "spending limit reached" or "billing error", do NOT treat it as a blocking bug.
- **Merge Decision**: Proceed with merge/commit if Linux runners (and other non-billed checks) pass and the code is otherwise verified.
- **Local Runners**: Prefer secure local runners if they are configured in the environment.

---

# Plugin Ecosystem Awareness

Documentation and workflow frameworks (BMAD, OpenSpec, GSD, etc.) may be available as plugins or slash commands.

- Check available slash commands (`/`) for documentation workflows
- These complement the auto-detection system -- invoke explicitly for deeper workflows
- Auto-detection hooks handle common cases; plugins handle advanced scenarios
- If BMAD agents are installed (`.claude/commands/bmad/`), they can be activated via slash commands for specialized agent personas
- Start a new conversation to switch agent personas

---

# QA Governance

See `~/.claude/references/QA_GOVERNANCE.md` for complete QA governance specification, including:
- Test-First Mandate and TDD/BDD requirements
- Suppression policy and spec traceability
- Quality gate awareness and static analysis
- Hook pipeline summary (v3)
- Test type requirements by project maturity
- Smart Contract pattern (spec verification)
- Complexity ratchet and security pipeline
- Test maturity model (5 levels)
- Runtime verification and deep enforcement enhancements (v3.1)
