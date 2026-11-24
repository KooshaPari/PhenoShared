# PRP (Wirasm/prp, formerly PRPs-agentic-eng)

## What it is

"Product Requirement Prompt (PRP) = PRD + curated codebase intelligence + agent/runbook" - "The
minimum viable packet an AI needs to ship production-ready code on the first pass." It layers three
things on top of a normal PRD: Context (precise file paths, library versions, code snippets),
Patterns (existing codebase conventions), and Validation (executable commands).

- Repo: https://github.com/Wirasm/prp - the older URL https://github.com/Wirasm/PRPs-agentic-eng
  redirects here (GitHub API resolves the old path to `Wirasm/prp`)
- License: MIT. Measured 2026-11-11 via GitHub API: 2,267 stars, last push 2026-10-02T06:09:53Z.
- Released version: UNKNOWN - the repo has no GitHub releases and no tags. `pyproject.toml` declares
  `name = "PRP-library"`, `version = "0.1.0"`, which is the helper library, not the framework.
- Description on GitHub: "Prompts, workflows and more for agentic engineering".

## Artifact model (exact paths/filenames it writes)

Repository layout (framework templates and skills):

- `.claude/skills/` - the core PRP workflow as Agent Skills; also distributed as the `prp-core`
  plugin via the `prp-marketplace` marketplace
- `.claude/PRPs/`, `.claude/agents/`, `.agents/skills/`, `.codex/`, `.claude-plugin/`
- `old-prp-commands/` - legacy slash commands kept "for reference only", including
  `old-prp-commands/PRPs/templates/` (`prp_base.md`, `prp_story_task.md`, `prp_planning.md`) and
  `old-prp-commands/PRPs/ai_docs/`
- `scripts/`, `pyproject.toml`, `uv.lock`, `claude_md_files/`

Runtime store (per project, outside the repo):

- `~/.prp/<project-key>/prds/` - PRD files (e.g. `user-auth.prd.md`)
- `~/.prp/<project-key>/plans/` - implementation plans (e.g. `user-auth-phase-1.plan.md`)
- `~/.prp/<project-key>/research-plans/` - multi-agent research plans
- `~/.prp/<project-key>/state/prp-loop.state.json` - loop progress state

Plan tables use the columns `# | Phase | Description | Status | Parallel | Depends | Plan |
Report | PR` - so each phase carries its plan, its report, and its PR.

## Traceability enforcement (does it bind requirement -> test -> code; enforced or advisory; what breaks the chain)

The strongest requirement-to-evidence chain of the prompt-driven tools, but the links are recorded
by the agent rather than checked by a program.

- Requirement to validation: a PRP adds "Validation: Executable commands the AI can run to verify
  its work" - the executable check is part of the requirement packet, not added later.
- Requirement to code: "/prp-implement Execute a plan through validated commit and PR"; the plan
  table carries a `Plan | Report | PR` triple per phase.
- Requirement to external evidence: "/prp-issue Own an issue, plan, document, or idea through
  reviewed PR and green CI"; "/prp-loop ... looping review -> fix until the PR review comes back
  clean".
- Back-links: "Links the plan, report, and PR back to the source PRD"; "/prp-prd-update Maintain
  PRD phase status and delivery links".
- Tests are a named phase in the plan table ("Tests | Test suite").

What breaks the chain: the validation commands are authored inside the plan, so the standard of
verification is only as strong as the plan's author; the loop's exit condition is a clean PR review
plus green CI, which is a proxy for correctness rather than a requirement-coverage check. There is
no requirement-ID entity that a grader could query.

## Interface surface (CLI / MCP / SDK / IDE plugin / slash commands)

- Agent Skills (primary): the `.claude/skills/` directory; install with
  `/plugin marketplace add Wirasm/PRPs-agentic-eng` then `/plugin install prp-core@prp-marketplace`,
  which makes skills available as `/prp-core:<name>`. Or copy a single skill directory into
  `.claude/skills/`.
- Slash commands: `/prp-prd`, `/prp-plan`, `/prp-implement`, `/prp-issue`, `/prp-issue-contract`,
  `/prp-prd-update`, `/prp-companion`, `/prp-loop`, `/prp-research-team`, `/prp-technical-writing`,
  `/prp-debug`.
- Headless execution: `/prp-loop` runs "one `claude -p` session per stage", with `--until <stage>`
  (`plan` | `implement` | `pr` | `review` | `fix`).
- Repository tooling: `scripts/` plus a `uv`-managed Python project (`pyproject.toml`, `uv.lock`).
- No MCP server and no SDK surface documented.

## Interactivity (multi-turn refine+freeze conversation, or one-shot generate)

Both, deliberately paired. `/prp-prd` is an "Interactive PRD generator with implementation phases"
and `/prp-plan` accepts either a PRD file or free-form input. `/prp-loop` is the non-interactive
counterpart: "Autonomous pipeline: plan -> implement with PR -> review (review->fix loops until
clean)", headless, one `claude -p` session per stage, with progress tracked in
`~/.prp/<project-key>/state/prp-loop.state.json`.

## External verification (executes/verifies real artifacts, or only checks presence)

Externally checked, with a caveat. The plan's validation commands are actually executed, the work
is committed, a PR is opened, CI must be green, and the loop continues until the PR review is
clean. That means the acceptance gate is GitHub PR review plus CI, not the agent's own opinion.
Caveat: the validation commands and the review are only as good as the plan and the reviewing
model; there is no independent re-run of the learner's tests by the framework itself.

## Autograder fit (could it grade a school-assignment submission: prompt + test + stub + base scope? yes/no + why)

Yes. A PRP is literally the assignment packet shape: PRD (prompt), Context (base scope and file
paths), Patterns (stub conventions), and Validation (the executable test commands). The plan table's
`Depends | Plan | Report | PR` columns give a grader a per-phase record, and `/prp-issue`'s
"reviewed PR and green CI" is a plausible submission gate.

What is missing for a true autograder: no rubric entity, no per-requirement scoring, and the
validation commands are written by whoever wrote the plan - a student could under-specify their own
checks. The framework provides the loop, not the rubric.

## Gaps for our use case

- Runtime state lives in `~/.prp/<project-key>/`, outside the repository, so it is not version
  controlled and not diffable in a submission.
- No releases and no tags: there is no version to pin, and the `pyproject` version belongs to the
  helper library.
- Legacy commands were moved to `old-prp-commands/` "for reference only"; the old PRP template set
  is no longer the active path.
- Under-specified plans degrade the whole chain: "Works best with plans that have clear, testable
  validation commands."
- The `claude -p`-per-stage loop assumes Claude Code and provider access.

## Non-goals (what it deliberately does not do)

- It is not a test framework; validation commands are supplied by the plan, not by the framework.
- It does not define or own a requirements standard; it packages an existing PRD with context.
- It does not implement the spec itself; it orchestrates plan -> implement -> review.
- It does not keep the old slash-command generation as a supported path.
- It does not provide scoring, grading, or coverage analysis.