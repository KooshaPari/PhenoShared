# Airlock V2 — Architecture Overview

**Date:** 2026-07-15
**Purpose:** persistent infrastructure to prevent lost-work incidents for
every agent running on this Mac.

---

## The problem this solves

Over the last several weeks we have had two classes of lost-work incident:

1. **Agent dies mid-session.** A Codex / Claude / Cursor session
   ends (timeout, OOM, network drop, accidental Ctrl-C) and leaves dirty
   edits sitting in working trees. The agent was supposed to commit on
   completion but never got the chance.
2. **Branch explosion.** Work-in-progress proliferates as hundreds of
   `wip/*` branches across every repo. Each individual branch is a small
   bundle of work; **their consolidated loss is hard to notice** until a
   recovery audit finds them orphaned.

Airlock V2 provides the missing infrastructure in three layers:

| Layer | Component | Cadence |
|---|---|---|
| Edge (per agent)   | **Airlock V2 Hooks** (Codex, Claude, Cursor)            | every agent tool call |
| Standby            | **Auto-Commit Daemon**                                | every 15 minutes |
| Garbage collection | **Cleanup Daemon** (consolidator + stale archiver)    | every 8 hours |

The system is intentionally **conservative on deletes** (no branch is ever
deleted unless its content is provably backed up to origin) and **aggressive
on saves** (every dirty change gets a wip/* branch within minutes).

---

## Components

### A. Airlock V2 Hooks

Path: `hooks/airlock-v2-hook.sh` (one shell script, three config files).

| Agent    | Config file                                | Trigger supported |
|----------|--------------------------------------------|-------------------|
| Codex    | `~/.codex/config.toml` or `~/.codex/hooks.json` | `PostToolUse`, `Stop` |
| Claude Code | `~/.claude/settings.json`              | `PostToolUse`, `Stop`, `SessionStart` |
| Cursor   | `~/.cursor/cli-config.json` (permissions) + project-level instructions | invoked by agent |
| thegent  | pass-through via existing thegent-hook-init | `PreToolUse`, `PostToolUse`, `Stop` |
| forge, gemini, copilot, droid, factory, aider | manual invocation with `AIRLOCK_V2_AGENT=<name>` | per-call |

The hook script:

1. Reads the agent's event JSON on **stdin** (Codex and Claude's format).
2. Extracts the cwd from the JSON (tries `.cwd`,
   `.working_directory`, `.session.cwd`, `.tool_input.cwd`, etc. — falls
   back to `$PWD`).
3. Resolves the cwd to a git toplevel.
4. **Refuses** to act if the toplevel is **not** under
   `~/CodeProjects/Phenotype/repos/`. This is the safety boundary.
5. If the tree is dirty:
   - `git add -A`
   - create/switch branch `wip/<UTC YYYY-MM-DD-HHMM>-<agent>-<event_id>`
   - commit with metadata footer
   - push to `origin` (best-effort, no force-push)
   - best-effort notify the airlock v1 daemon via Unix socket
6. Logs to `~/.airlock-v2/logs/hook.log` with structured fields.

The script never returns a non-zero exit code on a benign failure — it
**always** exits 0 (unless the working tree is outside the REPO_ROOT, in
which case it exits 1 silently so agents don't see scary error messages
for edits to `/tmp` etc.).

### B. Auto-Commit Daemon

Path: `daemons/auto-commit-daemon.py`
Launchd plist: `daemons/com.phenotype.auto-commit-daemon.plist`
Default interval: 900 seconds (15 minutes).

`--once` mode runs a single sweep and exits (used by the smoke test).
`--loop` mode runs forever, sleeping between sweeps and waking on signal.

A sweep:

1. **Probe** the airlock v1 daemon via `~/.airlock/socket`. If the daemon is
   busy (socket present but no quick health reply), skip the whole sweep.
   This prevents the new auto-commit daemon from piling on a wedged v1
   daemon.
2. **Walk** `~/CodeProjects/Phenotype/repos/` for git working trees.
3. For each tree:
   - skip if already on a `wip/*` branch (the hook will handle it);
   - skip if clean;
   - else `git add -A`, then create branch `wip/<date>-auto`, commit,
     push (best-effort).
4. Log a structured summary of the sweep.

Safety:

- `fcntl.flock` re-entrancy guard on `/tmp/airlock-v2.auto-commit.lock`.
- Honors SIGTERM / SIGINT / SIGHUP for graceful shutdown.
- Never deletes branches.
- Never force-pushes.
- The push is `origin $branch:$branch`, not `--force-with-lease`; if a
  prior wip branch already exists with different commits, we leave it
  alone and let the cleanup daemon handle the discrepancy.

### C. Cleanup Daemon

Path: `daemons/cleanup-daemon.py`
Launchd plist: `daemons/com.phenotype.cleanup-daemon.plist`
Default interval: 28 800 seconds (8 hours).

A sweep has two halves:

#### C.1 — Branch consolidation

For each git working tree under `~/CodeProjects/Phenotype/repos/`:

1. List all `wip/*` branches (local + `origin/wip/*`).
2. List all `wip/*-consolidated` branches on origin (newest first).
3. Pick a base:
   - If a consolidated branch exists, base the new consolidation on its tip.
   - Else base on the repo's default branch (`refs/remotes/origin/HEAD`
     → fallback `main` → `master`).
4. Create new branch `wip/<UTC YYYY-MM-DD-HHMM>-consolidated` from base.
5. For each source branch in chronological order, run
   `git merge --no-ff`. On conflict, abort and retry with
   `git merge --squash` (conservative: no history rewrite, but loses
   intermediate commits).
6. Force-push with `--force-with-lease`. **`--force-with-lease` is
   deliberate** — it will refuse to clobber an external commit
   introduced since we last fetched.
7. Verify on origin via `git ls-remote`. Only if the SHA matches do we:
   - delete each source branch locally with `git branch -D`;
   - delete each source branch on origin with `git push origin --delete`.
   Both are gated by `git merge-base --is-ancestor <src> HEAD` so we
   cannot delete a branch whose tip is not in the consolidated branch.
8. If verification fails, log a warning and **leave all source
   branches alone** for the next sweep to try.

#### C.2 — Stale airlock v1 entry archival

The daemon opens the airlock v1 SQLite database in **read-only** mode and
finds `repos` rows older than `AIRLOCK_V2_ARCHIVE_DAYS` (default 30 days).
For each:

1. `tar --zstd` the `~/.airlock/repos/<id>/` subtree to
   `_phenofleet-decisions/airlock-cleanup/<id>.tar.zst`.
2. Stream-compute the sha256 of the resulting file.
3. Write sidecar `<id>.sha256` with `<digest>  <file>`.

**The original `~/.airlock/repos/<id>` directory is NEVER deleted by this
daemon.** Only humans can delete airlock entries. The daemon's job is to
make deletion safe by providing an offsite backup; the human's job is to
delete the original after they trust the archive.

---

## Why these intervals?

- **15 minutes** for auto-commit: short enough that a panicked agent that
  dies can only lose ~15 minutes of unconfirmed work; long enough that we
  don't churn git every keystroke.
- **8 hours** for cleanup: long enough that 95% of agent sessions finish
  and their wip/* branches accumulate into a meaningful consolidation.
  Short enough that branches don't grow into the thousands.
- **Per-tool-call** for the hook: that latency is unavoidable for safety,
  but every call is bounded by 30 seconds so a wedged hook can never block
  the agent.

---

## Branch naming convention

| Trigger | Branch name |
|---|---|
| Codex / Claude / Cursor hook | `wip/<UTC YYYY-MM-DD-HHMM>-<agent>-<event_id>` |
| Auto-commit daemon (15min)    | `wip/<UTC YYYY-MM-DD-HHMM>-auto` |
| Cleanup daemon consolidation  | `wip/<UTC YYYY-MM-DD-HHMM>-consolidated` |
| Smoke test                    | `wip/smoke-test-<pid>` |

The `<date>-<tag>` ordering gives chronological sort. UTC timestamps are
used so changes from machines in different time zones sort correctly.

---

## Failure modes & mitigations

| Failure | Mitigation |
|---|---|
| Airlock v1 daemon unresponsive | Auto-commit skips the sweep, logs `sweep_skipped` |
| `git push` rejected (history divergence) | Hook logs `push: failed`, branch is local-only, cleanup retries later |
| Network down during cleanup | `git fetch` fails, consolidation aborted safely, branches left as-is |
| User force-kills the daemon (`pkill -9`) | Next sweep re-locks cleanly; SIGTERM-friendly code path is preferred |
| Hook runs on a `/tmp/` edit | Toplevel not under REPO_ROOT → silent skip with exit 1 |
| Hook runs concurrently with itself | Each call uses a unique event_id → no branch-name collision |
| Two simultaneous cleanup runs | `fcntl.flock` re-entrancy guard on `/tmp/airlock-v2.cleanup.lock` |

---

## What this does NOT do

- **No force-push on per-event hooks.** Only the cleanup daemon force-pushes
  (with `--force-with-lease`), and only the consolidated branch.
- **No remote deletion without backup.** Wip/* deletion is gated on
  `ls-remote` confirming the consolidated branch holds the source tip.
- **No deletes of airlock v1 entries.** Archived, never auto-purged.
- **No modifications to `~/.airlock/`.** Airlock V2 reads the airlock v1
  SQLite database read-only.
- **No network exposure.** All communication is via Unix sockets or
  loopback. No inbound ports.
- **No force-updates of other agents' working trees.** Each hook only
  touches the cwd of the agent that fired it.

---

## File map

```
_phenofleet-decisions/airlock-v2/
├── README.md                     <- this file
├── INSTALL.md                    <- install guide + safety summary
├── airlock-v2-smoke-test.sh      <- end-to-end smoke test
├── hooks/
│   ├── airlock-v2-hook.sh        <- the hook (Codex/Claude/Cursor all use this)
│   ├── codex-hooks.json          <- Codex hook config (TOML inline + JSON)
│   ├── claude-hooks.json         <- Claude Code hook config
│   └── cursor-hooks.json         <- Cursor permissions+future hooks config
└── daemons/
    ├── auto-commit-daemon.py
    ├── com.phenotype.auto-commit-daemon.plist
    ├── cleanup-daemon.py
    └── com.phenotype.cleanup-daemon.plist
```

Runtime artifacts (created by the daemons, not shipped):

```
~/.airlock-v2/
├── logs/
│   ├── hook.log                  <- structured JSONL of every hook invocation
│   ├── auto-commit.log           <- daemon sweep start/done lines
│   ├── auto-commit.stdout.log    <- launchd stdout capture
│   ├── auto-commit.stderr.log    <- launchd stderr capture
│   ├── cleanup.log
│   ├── cleanup.stdout.log
│   ├── cleanup.stderr.log
│   └── smoke-hook.log            <- only when running smoke tests
└── (lock files live at /tmp/airlock-v2.{auto-commit,cleanup}.lock)

_phenofleet-decisions/airlock-cleanup/
└── <id>.tar.zst                  <- stale airlock v1 entry archives
└── <id>.sha256                   <- sidecar sha256 digest
```

---

## Audit

The deliverable audit lives at
`_phenofleet-decisions/airlock-v2/.subagent-5-airlock-v2-audit-2026-07-15.json`.
It records what was built, line counts, syntax-check results, and smoke-test
results.

---

**End of architecture overview.**
