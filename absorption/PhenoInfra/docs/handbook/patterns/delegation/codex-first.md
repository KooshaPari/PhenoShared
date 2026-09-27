# Agent delegation: codex-spark first

**Status:** adopted · **Applies to:** any work fanned out to coding agents.

## Channel priority

1. **codex-spark — PRIMARY.** `codex exec -m gpt-5.3-codex-spark -c model_reasoning_effort=medium`. Cheap, fast, high capacity. Use it for the bulk of compile-grind and mechanical work. On quota, fall back to `gpt-5.4-mini`.
2. **Composer 2.5 — SPARINGLY.** Pricey and monthly-bound; reserve for high-judgment work needing a fast Opus-alternative.
3. **Native Claude Agent — judgment & vision.** Reserve for tasks needing reasoning, design taste, or reading screenshots.

Avoid Sonnet/Haiku for new delegation — they lag the channels above.

> Note: codex's subprocess spawning is fragile on Windows (it shells out to pwsh). When it fails with `process error -1073741502` or hits interactive `gh` prompts, drive the git/PR work directly from your own shell instead of retrying the agent.

## Parallel-work rules

- Each parallel worker gets a **disjoint set of files**. Never point two workers at the same file.
- A mutating worker runs in its **own git worktree + branch**, then merges centrally. Don't share one branch and reconcile collisions live.
- **Never `git stash`.** Commit dirty work to a WIP branch (durable, visible) or keep working dirty.
- Pass explicit flags to non-interactive tools (`gh pr create -R … -H … -B … --title --body`) so nothing blocks on a prompt.

## Why

Routing volume to the cheapest capable channel preserves the expensive channels' budget for the judgment calls only they can make. Disjoint files + per-worker worktrees make parallelism safe without live conflict resolution.
