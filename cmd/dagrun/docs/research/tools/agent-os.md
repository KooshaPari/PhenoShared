# Agent OS (buildermethods/agent-os)

## What it is

A free, open-source system for defining, discovering, and injecting coding standards into AI
coding agents. It is not a spec-driven workflow engine in the spec-kit sense; it is the layer that
answers "what does this codebase consider correct?" so that agents write code that matches it.

- Repo: https://github.com/buildermethods/agent-os (MIT)
- Product page: https://buildermethods.com/agent-os
- Measured 2026-11-11 via GitHub API: 5,593 stars, 832 forks, latest release v3.0.0
  (published 2026-01-20), last push 2026-10-07T04:18:58Z.

Stated core capabilities (README): "Discover Standards", "Deploy Standards", "Shape Spec",
"Index Standards". v3 "discovers and documents those standards for you". It is "designed to
complement tools like Claude Code, Cursor, and other AI assistants, not replace them", and "works
alongside Claude Code, Cursor, Antigravity, and other AI tools".

## Artifact model (exact paths/filenames it writes)

- Repo-shipped components: `commands/agent-os/` (Claude Code slash-command definitions),
  `profiles/` (per-tool profiles), `scripts/project-install.sh`, `scripts/common-functions.sh`,
  `scripts/sync-to-profile.sh`, and `config.yml`.
- Project output: an `agent-os/` directory of Markdown files in the target repository. The product
  page states "since all outputs are markdown files, Agent OS works just as well with any AI tool
  ... For tools other than Claude Code, simply reference the underlying files in `agent-os/`
  directly."
- Documented flow pages: `/agent-os/installation`, `/agent-os/discover-standards`,
  `/agent-os/inject-standards`, `/agent-os/shape-spec`.

Exact filenames inside `agent-os/` (standards file names, spec file name, plan file name):
UNKNOWN - the per-page file listings were not read. The repository tree exposes only the
directories above.

## Traceability enforcement (does it bind requirement -> test -> code; enforced or advisory; what breaks the chain)

NONE. Agent OS has no requirement artifact that binds to tests or code. It injects standards
("Intelligently inject relevant standards based on what you're building") and shapes specs with
questioning. Nothing in the documented capabilities links a spec line, a test, and a code path.

Enforcement style: advisory. Standards are injected into the agent's context; the agent is expected
to comply. No mechanism validates that the produced code matches the injected standard.

What breaks the chain: the chain does not exist to begin with - the only artifacts are standards
and shaped specs. If a grader needs requirement -> test -> code binding, Agent OS contributes only
the "standards" and "spec shaping" halves of that chain.

## Interface surface (CLI / MCP / SDK / IDE plugin / slash commands)

- Slash commands: "designed primarily for Claude Code, with slash commands that integrate directly
  into your workflow". The repo ships `commands/agent-os/`.
- Shell installer: `scripts/project-install.sh` (referenced by the installation guide), with
  `sync-to-profile.sh` for per-tool profiles.
- Tool-agnostic: works with "Claude Code (recommended) - Full integration with slash commands",
  Cursor, Windsurf, Codex, "Any AI coding assistant that can read files".
- No MCP server and no SDK/library surface documented.

## Interactivity (multi-turn refine+freeze conversation, or one-shot generate)

Multi-turn during spec shaping: "Enhanced shaping questions (run in plan mode) help you create
stronger, more aligned specs that account for your product's mission and all your standards."
Standards discovery is an agent-driven scan of the existing codebase ("Extract patterns and
conventions from your codebase into documented standards"), and injection is relevance-based at
prompt time.

Whether a fully non-interactive/headless invocation of the discovery or shaping flows exists:
UNKNOWN.

## External verification (executes/verifies real artifacts, or only checks presence)

Neither. No test execution, no lint gate, no CI integration is described. Discovery inspects the
codebase and writes Markdown; injection puts text in context. There is no external artifact check
in the documented flow - the only "verification" is the human reading the generated standards or
the shaped spec.

## Autograder fit (could it grade a school-assignment submission: prompt + test + stub + base scope? yes/no + why)

No, not as a grader. It could serve two supporting roles for an assignment harness: (a) hold the
course's coding standards as injected context so a submission is written against the rubric, and
(b) shape the assignment spec (the prompt/stub/base scope) via its shaping questions. It provides
no way to execute the learner's tests, score acceptance criteria, or detect a spec violation.

## Gaps for our use case

- No requirement-level artifact, no acceptance criteria model, no task decomposition.
- Standards are Markdown prose; there is no machine-readable rule format, so they cannot be
  evaluated programmatically.
- Relevance-based injection is heuristic ("Intelligently inject relevant standards"), so coverage
  is not guaranteed - a relevant standard that is not injected cannot be enforced.
- Output is Markdown only, so any structured consumption requires our own parsing.

## Non-goals (what it deliberately does not do)

- It does not replace the coding agent or the build toolchain: "It's designed to complement tools
  like Claude Code, Cursor, and other AI assistants, not replace them."
- It is not a spec-to-code generator; it shapes plans and standards that other tools execute.
- It is not a test or CI harness; no verification step is offered.
- It is not a hosted service dependency: "all outputs are markdown files", usable by any tool that
  can read files.