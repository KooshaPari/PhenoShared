# aider (Aider-AI/aider)

## What it is

AI pair programming in the terminal. Aider edits your local git repository, commits automatically,
and - for this study - matters because of its conventions mechanism: a plain Markdown file loaded
read-only into the chat so the model follows your coding guidelines.

- Repo: https://github.com/Aider-AI/aider (Apache-2.0)
- Conventions docs: https://aider.chat/docs/usage/conventions.html
- Community conventions repo: https://github.com/Aider-AI/conventions
- Measured 2026-11-11 via GitHub API: 50,061 stars, 5,155 forks, last push 2026-05-22T14:02:20Z.
  Latest GitHub release v0.86.0 (published 2025-08-09); the newest tag is `v0.86.3.dev`.

## Artifact model (exact paths/filenames it writes)

- `.aider.conf.yml` - configuration; the conventions hook is the `read` key:
  `read: CONVENTIONS.md` or `read: [CONVENTIONS.md, anotherfile.txt]`.
- `CONVENTIONS.md` - the conventions file itself (any Markdown; the docs use this name as the
  running example). It is a read-only context file, not an output artifact.
- aider's own chat/edit history files in its session directory (not specified in the docs read).
- Git commits: "Aider automatically commits changes with sensible commit messages."
- Repo-map artifacts are in-memory; the repo map is described at https://aider.chat/docs/repomap.html.

## Traceability enforcement (does it bind requirement -> test -> code; enforced or advisory; what breaks the chain)

NONE. Conventions are guidelines, not requirements. The docs' example is a preference list
("Prefer httpx over requests", "Use types everywhere possible"), and the only enforcement is that
the file is in context: "It's best to load the conventions file with /read CONVENTIONS.md or
aider --read CONVENTIONS.md. This way it is marked as read-only, and cached if prompt caching is
enabled."

The docs demonstrate the effect by example, not by check: the same task produced `import httpx` with
type hints when the conventions file was loaded, and `import requests` without types when it was
not ("GPT correctly used httpx and provided type hints").

What breaks the chain: there is no requirement artifact to trace from, so the chain cannot exist.
Compliance is a model behaviour, verified by reading the diff, not by a tool.

## Interface surface (CLI / MCP / SDK / IDE plugin / slash commands)

- CLI: `aider` (interactive), `aider --read CONVENTIONS.md useragent.py`, plus `--message` for
  one-shot runs and `--model` for model selection.
- In-chat slash commands: `/read`, `/add`, `/diff`, `/commit`, `/lint`, `/test`, `/run`, `/undo`,
  `/web`, `/ask` (the commands reference page is https://aider.chat/docs/usage/commands.html).
- Config file `.aider.conf.yml` (YAML, also settable per-flag).
- No MCP server, no plugin/IDE surface, and no SDK surface documented.

## Interactivity (multi-turn refine+freeze conversation, or one-shot generate)

Interactive by default: a REPL conversation in the terminal where the model proposes edits and the
user approves or rejects them. One-shot generation is available via `--message`/`--yes` for
scripted runs. There is no spec-capture conversation: the "spec" is whatever context files you
load plus what you type.

## External verification (executes/verifies real artifacts, or only checks presence)

Real execution, but only of what you configure. "Automatically lint and test your code every time
aider makes changes. Aider can fix problems detected by your linters and test suites." So aider
runs your lint and test commands after edits and can iterate on failures - but there is nothing
requirement-derived in the loop; the check set is whatever the project already defines.

## Autograder fit (could it grade a school-assignment submission: prompt + test + stub + base scope? yes/no + why)

No. Aider is an execution substrate, not a grader. It could be the component that runs a student's
tests, shows the failure, and lets the student iterate (its lint/test loop), and the conventions
file can carry the assignment's style rules into the submission. But it has no rubric, no
requirement model, no submission state, and no scoring - so it cannot decide pass/fail.

## Gaps for our use case

- No specification artifact: nothing to hang acceptance criteria on.
- Conventions are soft prose; the "enforcement" is a different model response, and the same prompt
  produced different code with and without the file.
- Context cost: the conventions file occupies the context window every session it is loaded into
  (cached when prompt caching is on).
- Verification requires you to already have lint/test commands configured; aider adds no
  requirement-derived checks.
- Last push 2026-05-22 and latest release v0.86.0 (2025-08-09): the project is in low-activity
  maintenance relative to the SDD tools.

## Non-goals (what it deliberately does not do)

- It is not a spec-driven workflow: it does not create specifications, plans, or task lists.
- It is not a task tracker or requirements manager.
- It does not define or enforce a traceability chain; it applies conventions.
- It is not a test framework - it invokes your existing linters and test suites.
- It does not act autonomously in a loop without you approving edits (one-shot modes are explicit
  flags).