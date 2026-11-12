# cc-sdd (gotalab/cc-sdd)

## What it is

An MIT-licensed SDD harness that installs an agentic SDLC workflow as Agent Skills for eight
coding agents. It reproduces Kiro's spec-driven style outside the Kiro IDE: "Kiro-inspired.
Similar spec-driven, agentic SDLC style as Kiro IDE. Existing Kiro specs remain compatible and
portable." Its differentiator is long-running autonomous implementation with per-task independent
review.

- Repo: https://github.com/gotalab/cc-sdd (MIT)
- npm: `cc-sdd` (npm reports version 3.1.0, license MIT)
- Measured 2026-11-11 via GitHub API: 3,762 stars, 287 forks, latest GitHub release v3.1.0
  (published 2026-09-23), last push 2026-10-22T03:43:11Z.

Design stance (README): "cc-sdd treats the spec as a contract between parts of the system, not a
master command document handed to the agent. Code remains the source of truth. Specs make the
boundaries between parts of the code explicit so humans and agents can work in parallel without
constant synchronization." "Agents write the spec, humans approve the contract at phase gates,
code is what ships."

## Artifact model (exact paths/filenames it writes)

- Spec directory: default `.kiro/`, overridable with `--kiro-dir docs`. The repo ships both
  `.kiro/settings` and `.kiro/specs` plus `.agents/skills`.
- Per spec: `requirements.md` (EARS-format requirements with acceptance criteria), `design.md`
  (architecture with Mermaid diagrams and a File Structure Plan), `tasks.md` (implementation tasks
  with boundaries and dependency annotations).
- Discovery outputs: `brief.md`, and `roadmap.md` when the work decomposes into multiple specs.
- Customization tree `{{KIRO_DIR}}/settings/`: `templates/` (document structure for requirements,
  design, tasks) and `rules/` (AI generation principles and judgment criteria).
- Task annotations inside `tasks.md`: `_Boundary:_` and `_Depends:_`; learnings accumulate under
  an `## Implementation Notes` heading.
- Installer also writes the 17 skills into each agent's skill directory (one skill set per agent).

## Traceability enforcement (does it bind requirement -> test -> code; enforced or advisory; what breaks the chain)

Partially enforced, at task granularity, by process rather than by a machine-checked graph.

- Requirements are EARS-format with acceptance criteria, which is the requirements-to-test bridge
  ("WHEN [condition] THE SYSTEM SHALL [behaviour]" style, mirrored from Kiro's requirements model).
- Design-to-code boundary binding: "design.md now includes a File Structure Plan that drives task
  boundaries. Tasks carry `_Boundary:_` and `_Depends:_` annotations. Review and validation look
  for boundary violations, not just style issues."
- Test-first per task: "/kiro-impl for long-running autonomous implementation ... each task gets a
  fresh implementer running TDD (RED -> GREEN) behind a feature flag, an independent reviewer, and
  an auto-debug pass when blocked or after repeated review rejection."
- Cross-spec consistency for multi-spec work: "/kiro-spec-batch ... with cross-spec review to
  catch contradictions, duplicated responsibilities, and interface mismatches."

What is advisory: the requirement-to-task and task-to-test-file links are not verified by a tool;
they are checked by a reviewing agent (inline review when no native subagents exist) and by human
approval at phase gates. Code stays the source of truth, so a spec that drifts from the code is
resolved in favour of code. The reviewer is a model, not an independent test harness.

## Interface surface (CLI / MCP / SDK / IDE plugin / slash commands)

- CLI installer: `npx cc-sdd@latest`. Flags observed in the README: `--claude-skills` (default),
  `--codex-skills`, `--cursor-skills`, `--copilot-skills`, `--devin` / `--devin-skills`,
  `--opencode-skills`, `--gemini-skills`, `--antigravity`, `--lang <14 languages>`, `--dry-run`,
  `--kiro-dir <dir>`.
- Slash commands / Agent Skills (17 per install): `/kiro-discovery`, `/kiro-spec-init`,
  `/kiro-spec-requirements`, `/kiro-spec-design`, `/kiro-spec-tasks`, `/kiro-impl`,
  `/kiro-spec-batch`, `/kiro-steering`, `/kiro-validate-gap`.
- Legacy command modes (`--claude`, `--cursor`, `--copilot`, `--opencode`, `--gemini`, `--qwen`)
  still work but are deprecated; `--codex` legacy mode is blocked.
- Stability: Claude Code and Codex stable; Cursor, Copilot, Devin Local/CLI, OpenCode, Gemini CLI,
  Antigravity beta; Windsurf/Cascade deprecated. "Installing 17 skills does not verify that a host
  can run the full autonomous loop."
- No MCP server and no SDK surface documented.

## Interactivity (multi-turn refine+freeze conversation, or one-shot generate)

Multi-turn with explicit phase gates. The flow is `kiro-discovery -> kiro-spec-init ->
kiro-spec-requirements -> kiro-spec-design -> kiro-spec-tasks -> kiro-impl`, and "agents write the
spec, humans approve the contract at phase gates". Discovery "writes brief.md (and roadmap.md when
multi-spec) and suggests the next command".

Non-interactive: `/kiro-impl` is the autonomous path - "recorded task state supports resumption
after checking unfinished work and active workers", so it is resumable across sessions. Whether
`kiro-impl` can be invoked with no human in the loop at all is only partially stated: "Native
subagents are used when available; hosts without them execute sequentially with inline review".

## External verification (executes/verifies real artifacts, or only checks presence)

Real execution, but performed by agents rather than by an independent system.

- TDD is actually run: the implementer executes RED then GREEN for each task.
- Independent review: "each task gets a fresh implementer ..., an independent reviewer, and an
  auto-debug pass when blocked or after repeated review rejection". Without native subagents,
  "implementation and review run inline" - so the reviewer is the same context.
- Review looks for concrete artifacts: boundary violations, cross-spec contradictions, duplicated
  responsibilities, interface mismatches.
- No separate CI gate or external test-runner integration is described.

## Autograder fit (could it grade a school-assignment submission: prompt + test + stub + base scope? yes/no + why)

Yes, the best-shaped fit among the prompt-driven tools. An assignment can be expressed as a spec
(`requirements.md` in EARS form with acceptance criteria), a `design.md` File Structure Plan that
defines the stubs/base scope boundaries, and `tasks.md` for the learner's incremental work. The
`_Boundary:_` / `_Depends:_` annotations give a grader a machine-readable-ish structural signal,
and the independent reviewer plus TDD RED/GREEN evidence give a per-task verification story.

Caveats that keep it from "yes, as-is": the reviewer is a model from the same harness, the RED/GREEN
evidence is the implementer's own report rather than a sealed test run, and code is declared the
source of truth, so a grader must not treat spec drift as a defect.

## Gaps for our use case

- No isolated execution sandbox: validation is the agent running commands in the working tree.
- No machine-checkable requirement-ID -> task-ID -> test-file trace; the reviewer infers it.
- Docs are Japanese-first (README links `README_ja.md`, `README_zh-TW.md`), English docs exist
  under `docs/guides/`.
- Multi-agent maturity is uneven: Copilot subagents depend on the client, Devin Cloud is out of
  scope, and "authenticated task execution is still unverified" for the new beta adapters.
- 17 skills x 8 agents is a large install surface; progressive disclosure mitigates context cost
  but not maintenance.

## Non-goals (what it deliberately does not do)

- It does not make the spec the source of truth: "Code remains the source of truth"; specs make
  boundaries explicit.
- It does not replace the coding agent; it installs skills into one.
- It does not ship a test framework, CI, or coverage tooling.
- It does not guarantee autonomous execution on every host: "Installing 17 skills does not verify
  that a host can run the full autonomous loop."
- It does not keep the legacy slash-command modes as a first-class path; they are deprecated.