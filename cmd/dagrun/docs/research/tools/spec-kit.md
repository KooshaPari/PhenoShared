# spec-kit (github/spec-kit)

## What it is

GitHub's open-source toolkit for spec-driven development (SDD). It ships processes, reusable
templates, and documented outcomes for an AI coding agent: build a feature (SDD), repair broken
behavior (bug fixing), or assess whether an idea deserves investment (idea assessment). The
methodology document states the core inversion: "Specifications don't serve code - code serves
specifications." Code is treated as the regenerated output of a specification plus implementation
plan, not as the source of truth.

- Repo: https://github.com/github/spec-kit (MIT, "Spec Kit is MIT licensed")
- Docs: https://github.github.io/spec-kit/
- Methodology: https://raw.githubusercontent.com/github/spec-kit/main/spec-driven.md
- Measured 2026-11-11 via GitHub API: 149,251 stars, 13,400 forks, latest release v1.4.0
  (published 2026-11-10), last push 2026-11-10T23:14:57Z.

## Artifact model (exact paths/filenames it writes)

`specify init <project> --integration <agent>` scaffolds a `.specify/` directory. Templates shipped
in the repo's `templates/` directory: `constitution-template.md`, `spec-template.md`,
`plan-template.md`, `tasks-template.md`, `checklist-template.md`, plus `commands/` and
`vscode-settings.json`.

Per-feature artifacts (documented in `spec-driven.md`):

- `specs/<branch-name>/spec.md` - the specification (user stories, acceptance criteria)
- `specs/<branch-name>/plan.md` - implementation plan, with constitutional phase gates
- `specs/<branch-name>/research.md` - research findings (e.g. library comparisons)
- `specs/<branch-name>/data-model.md` - entities and schemas
- `specs/<branch-name>/contracts/` - API specifications and event contracts
- `specs/<branch-name>/quickstart.md` - key validation scenarios
- `specs/<branch-name>/tasks.md` - executable task list (`[P]` marks parallel tasks)
- `memory/constitution.md` - the project constitution

Extension artifacts:

- `.specify/bugs/<slug>/` - bug assessment and fix reports; final verdict `verified` / `partial` /
  `failed`
- `.specify/assessments/<slug>/` - idea-assessment artifacts ending in `decision.md`
  (`go` / `needs-clarification` / `kill`)

The feature branch is generated from the description ("Creates branch '003-chat-system'").

## Traceability enforcement (does it bind requirement -> test -> code; enforced or advisory; what breaks the chain)

Advisory, template-and-prompt level. There is no machine-checked requirement-to-test-to-code graph.
The binding mechanism is textual and procedural:

- Constitution Article III (Test-First Imperative): "This is NON-NEGOTIABLE: All implementation MUST
  follow strict Test-Driven Development. No implementation code shall be written before: 1. Unit
  tests are written 2. Tests are validated and approved by the user 3. Tests are confirmed to FAIL
  (Red phase)."
- Constitution Article IX (Integration-First Testing): "Prefer real databases over mocks ... Use
  actual service instances over stubs ... Contract tests mandatory before implementation."
- Plan template File Creation Order: "1. Create `contracts/` with API specifications 2. Create test
  files in order: contract -> integration -> e2e -> unit 3. Create source files to make tests pass."
- Plan template "Phase -1: Pre-Implementation Gates" (Simplicity, Anti-Abstraction,
  Integration-First) act as "compile-time checks" the LLM must pass or justify in a "Complexity
  Tracking" section.
- Checklist templates are "unit tests" for the specification: "Requirements are testable and
  unambiguous", "Success criteria are measurable".
- `spec-driven.md`: "Every architectural decision traces back to specific requirements" and
  "Acceptance scenarios become tests ... test scenarios aren't written after code, they're part of
  the specification that generates both implementation and tests".

What breaks the chain: enforcement is the reviewing human plus the model's own checklist
self-review. Constitution Articles IV-VI are explicitly project-defined placeholders, so gates vary
per repo. No tool verifies a spec line maps to a test file, and the "Converged" verdict comes from
the same agent that wrote the code.

## Interface surface (CLI / MCP / SDK / IDE plugin / slash commands)

- CLI (primary): `uv tool install specify-cli` (needs Python 3.11+ and `uv`), then
  `specify init my-project --integration copilot`. Subcommands in the README: `specify extension
  add bug`, `specify extension add assess`, `specify extension search`, `specify preset search`,
  `specify workflow search`, `specify bundle search`.
- Slash commands / skills inside the agent chat: `/speckit-constitution`, `/speckit-specify`,
  `/speckit-plan`, `/speckit-tasks`, `/speckit-implement`, `/speckit-converge`; bug flow
  `/speckit-bug-assess`, `/speckit-bug-fix`, `/speckit-bug-test`; assessment flow
  `/speckit-assess-intake|research|define|shape|decide`.
- Many agent integrations ("more than 50 supported AI coding agents as of September 14, 2026" per
  https://www.augmentcode.com/guides/github-spec-kit-practical-guide-sdd-workflow); invocation
  syntax differs per agent.
- No MCP server and no SDK surface documented.
- Extensibility: Extensions, Presets, Workflows (overlays, custom steps), Bundles, Catalogs (public
  and private, with authentication), project-local template overrides.

## Interactivity (multi-turn refine+freeze conversation, or one-shot generate)

Multi-turn with human review between phases: "Run these skills in your agent's chat, not your
terminal, one at a time, reviewing each result before continuing." The spec template forces
clarifying questions instead of guesses via `[NEEDS CLARIFICATION: ...]` markers resolved by the
user before planning. Repeat implement and converge "until convergence reports `Converged`".

Non-interactive: commands can be driven headlessly through Workflows ("Automate prompts, commands,
gates, and shell tasks"); exact per-agent headless syntax is UNKNOWN from the README alone.

## External verification (executes/verifies real artifacts, or only checks presence)

Mostly self-reported by the agent, with one artifact-backed exception.

- Bug flow: "Review the reports in `.specify/bugs/login-crash/`. The final verdict is `verified`,
  `partial`, or `failed`; only `verified` confirms a successful fix." The verdict is produced by
  the agent's own run.
- Convergence: the agent reports the literal string `Converged`; the human repeats
  implement/converge until it appears.
- The constitution's Red-phase rule and the plan's test-first File Creation Order instruct the
  agent to write and run tests, but no independent CI or test-runner gate is documented; the
  checklists are presence and consistency checks.

## Autograder fit (could it grade a school-assignment submission: prompt + test + stub + base scope? yes/no + why)

Partial yes. It supplies the assignment scaffolding as prompt-level artifacts: `spec.md`
(requirements plus acceptance criteria), `plan.md` (technical scope and constraints), `tasks.md`
(granular task list), `contracts/` (interface stubs to implement), and `quickstart.md` (validation
scenarios). The constitution can carry grading policy (Article III test-first, plus a custom
Article IV/VI for course rules).

Why only partial: the grader is the same model that produced the submission, the checklist
mechanism checks the spec rather than the learner's code, and nothing binds a rubric line to a
specific learner test file. A separate execution step (CI running the learner's tests against the
provided stubs) is required and is outside spec-kit.

## Gaps for our use case

- No independent verifier: nothing runs the student's tests and diffs the result against the spec.
- Spec text is the only contract - no machine-readable requirement ID, no coverage or dependency
  graph, so "which requirement is unimplemented" is a model inference.
- Community catalogs are unaudited: "Catalog listings are not audits or endorsements, so review
  community source code before installing or running it." Installing an extension executes
  third-party commands.
- Branch and artifact naming derives from a free-text description, so parallel features need slug
  hygiene.
- The flow is one-at-a-time and human-gated; long unattended runs are not the default.

## Non-goals (what it deliberately does not do)

- It is a toolkit of processes and templates, not a test runner, CI system, or coverage tool.
- It does not implement the specification outside the agent: "Run these skills in your agent's chat,
  not your terminal".
- Bug fixing and idea assessment are not in the core flow; they are extensions you install on
  demand, and "No SDD feature workflow is required first" for either.
- It does not replace the coding agent: it "combines ready-to-use processes with composable
  mechanisms" and works "with your coding agent".
- It does not promise automatic spec-to-code regeneration in the released CLI; `spec-driven.md`
  states the philosophy ("Code becomes its expression") with "Continuous Refinement ... an ongoing
  refinement" rather than a mechanical rebuild command.