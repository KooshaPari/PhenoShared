# speckitty (spec-kitty/spec-kitty)

Source: /Users/kooshapari/CodeProjects/temp/proresearch-20261110/speckitty.md (primary: https://github.com/spec-kitty/spec-kitty)

## What it is

A Python CLI (spec-kitty-cli, MIT) that turns product intent into a repo-native governed agent workflow. Pipeline: spec -> plan -> tasks -> next -> review -> accept -> merge. Two differentiators versus Spec Kit: a "Charter" governance layer that governs how agents build (not only what), and git-worktree-per-work-package parallelism so several agents implement concurrently without branch chaos. Installed via pipx/uv tool; main carries a 4.0.0rc line, stable acceptance still pending.

## Artifact model (exact paths/filenames it writes)

Confirmed from the README:
- kitty-specs/ - repository-native mission artifacts: specs, plans, work packages, acceptance criteria, review state. Each mission addressed by <mission-slug>.
- .worktrees/ - isolated git worktrees, one per work package, for parallel agents.
- .kittify/config.yaml - project runtime config; documented keys include #retrospective (every completed mission emits a retrospective by default).
- retrospective.yaml - per-mission retrospective, authored at runtime terminus (HiC prompt or autonomous facilitator), explicitly not written by merge.

UNKNOWN: inner filenames under kitty-specs/<mission-slug>/ (whether spec.md / plan.md / tasks.md / per-work-package files). README names concepts and root folder but never prints a file tree; treat any claimed leaf filename as unverified. .worktrees/ collides with host worktree-layout policy, which bans worktrees/ containers.

## Traceability enforcement

Strongest of the four on lifecycle traceability, still weak on requirement -> test -> code. Work packages carry explicit lanes (planned, in_progress, for_review, approved, done), and review, accept, merge are separate commands with an audit trail, so nothing reaches done without a review path existing. spec-kitty dispatch "<request>" loads governance context, opens an "Op record", and returns the context the agent must use before working - enforcement by prompt-and-record, not filesystem assertion. spec-kitty next decides the next legal action, which constrains ordering. What breaks the chain: nothing binds a requirement to a test, and nothing verifies that the worktree diff satisfies the acceptance criteria - review is human/agent judgement. Acceptance criteria are stored, never compiled into executable checks.

## Interface surface

CLI: init, verify-setup, upgrade, next, dispatch, agent tasks status (--json for tools), retrospect summary, agent retrospect synthesize --apply. Slash commands / skills: /spec-kitty.charter, .specify, .plan, .tasks, .review, .accept, .merge --push, /spec-kitty-mission-review; on skill-based agents these become spec-kitty-<command> ($spec-kitty-specify in Codex, /skill:spec-kitty-specify in Pi). Agent integrations: Claude Code, Codex, Cursor, Gemini, Copilot, Windsurf, OpenCode, Qwen, Kiro, Vibe, Pi, Letta, Antigravity. MCP server and SDK: UNKNOWN (not in README; a host-surface-parity doc referenced but not fetched).

## Interactivity

Multi-turn and structured, not free-form. Conversational at the front (charter, then specify with natural-language intent), then gate-driven: plan and tasks derive from the spec and next dictates the next legal action rather than letting the agent choose. Freeze exists only as one-way lane advancement; no separate requirements-freeze ceremony and no immutable signed baseline in the README.

## External verification

Mixed, leaning presence-and-judgement. It really does: track lanes from stored state, derive next from that state, spawn real git worktrees, and produce a retrospective judged against the mission. It does not document running the project's tests, measuring coverage, or diffing implementation against acceptance criteria - verify-setup verifies installation wiring, not deliverables. So: real git operations, no documented behavioural grading.

## License

MIT.

## Notes

Duplicates AgilePlus almost exactly (work packages, lanes, governance records, acceptance criteria, retrospectives); .worktrees/ conflicts with host worktree policy; governance is prompt-and-record not an executable gate; no autograder, no assignment framing, no freeze ceremony; Python toolchain on a 4.0.0rc line with breaking changes between alpha releases.
