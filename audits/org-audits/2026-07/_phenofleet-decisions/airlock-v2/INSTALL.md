# Airlock V2 — Install Guide

**Audience:** anyone who wants agents (Codex, Claude, Cursor, thegent, forge,
gemini, copilot, droid, factory, aider) to **never lose their in-flight work**
and a periodic daemon to keep dirty repos from going stale.

**Scope:** This guide covers installation, smoke-test, and removal of the
three components shipped in this directory:

| Component | Purpose | Cadence |
|---|---|---|
| **Airlock V2 Hooks** (Codex, Claude, Cursor) | Auto-commit dirty work after every tool call / session stop | per-event (~milliseconds) |
| **Auto-Commit Daemon** | Background scan for dirty repos and `wip/-auto` commit | every 15 minutes |
| **Cleanup Daemon** | Consolidate `wip/*` branches, force-push consolidated, tarball stale entries | every 8 hours |

This is **additive**. It does **not** modify `~/.airlock/`, `~/.codex/`,
`~/.claude/`, or `~/.cursor/` config files automatically. You opt in per
component.

---

## Prerequisites

- macOS (tested on this Mac, hostname `MacBookPro.lan1`).
- Python 3.8+ on PATH (uses only stdlib).
- `git` on PATH.
- `bash` 3.2+ (the macOS default is fine).
- Optional: `jq` (the hook script will fall back to `python3 -c` if missing).
- Optional: `nc` (`netcat`) for airlock daemon bridge calls.
- Optional: `tar` with `--zstd` (Cleanup Daemon needs this for archives;
  every modern macOS has it).

Verify with:

```bash
python3 --version
git --version
which jq    # optional
which nc    # optional
tar --help  | grep -- '--zstd'
```

---

## Smoke-test (no install)

Before any install, run the smoke test to confirm everything is wired
correctly:

```bash
cd /Users/kooshapari/CodeProjects/Phenotype/repos/_phenofleet-decisions/airlock-v2
./airlock-v2-smoke-test.sh
```

This is **non-destructive**: it creates a temporary repo at
`~/CodeProjects/Phenotype/repos/.smoke-test-airlock-v2-<pid>/` and removes it
on exit. No agent config files, no `~/.airlock/`, no remote pushes.

If the smoke test prints `SMOKE TEST PASSED`, proceed to install.

---

## Component A — Airlock V2 Hooks

The hook script lives at:

```
hooks/airlock-v2-hook.sh
```

It is **the same script regardless of which agent's config you wire into**.
This is deliberate: it minimizes drift and makes it easy to audit.

### A.1 — Claude Code (recommended to install first)

Claude Code has the broadest hook support (PostToolUse, Stop, SessionStart).

1. Open `~/.claude/settings.json` in your editor.
2. Locate the `hooks` block (create it if absent).
3. Merge in the contents of `hooks/claude-hooks.json` (also in this dir).
   The script path is already absolute.

Quick check after merging:

```bash
jq -r '.hooks.PostToolUse[0].hooks[0].command' ~/.claude/settings.json
# should print the absolute path to airlock-v2-hook.sh
```

4. (Optional but recommended for Codex's hash-trust model): if you have
   `[hooks.state]` sha256-trust enabled for hooks, add the hook's sha256:

```bash
shasum -a 256 /Users/kooshapari/CodeProjects/Phenotype/repos/_phenofleet-decisions/airlock-v2/hooks/airlock-v2-hook.sh
```

### A.2 — Codex

Codex supports two config formats; both work:

- **JSON** (`~/.codex/hooks.json`): merge `hooks/codex-hooks.json`.
- **TOML** (`~/.codex/config.toml`): use the `[[hooks.post_tool_use]]` and
  `[[hooks.stop]]` blocks shown in the `_toml_equivalent` field of the JSON.

### A.3 — Cursor

Cursor 2026.07.08 has **no event-driven hook surface** today. The hook config
file (`hooks/cursor-hooks.json`) ships:

1. A `permissions.allow` entry so the agent can invoke the script via
   `Shell(/path/to/airlock-v2-hook.sh)`.
2. An `afterFileEdit`/`stop` block for the future (currently ignored).
3. An `_agent_instruction` reminder to add to your project's `AGENTS.md` or
   `CLAUDE.md` so Cursor voluntarily calls the hook after file edits.

Steps:

1. Open `~/.cursor/cli-config.json` and add the two `Shell(...)` entries from
   `permissions.allow` into the existing `permissions.allow` array.
2. Open your project's `AGENTS.md` and append:

   ```
   After every Edit/Write tool call, run:
     /Users/kooshapari/CodeProjects/Phenotype/repos/_phenofleet-decisions/airlock-v2/hooks/airlock-v2-hook.sh
   ```

### A.4 — Other agents (thegent, forge, gemini, copilot, droid, factory, aider)

These are supported via the same hook script (set `AIRLOCK_V2_AGENT` to your
agent name). Wiring them up depends on the agent:

- **thegent**: install the hook via your thegent config; pass
  `AIRLOCK_V2_AGENT=thegent` in the hook environment.
- **forge**: invoke `airlock-v2-hook.sh` manually as part of your loop.
- **aider**: wrap your `aider` invocation so it ends with a call to the hook.
- **gemini, copilot, droid, factory**: invoke via project-level instructions
  (similar to Cursor). Set `AIRLOCK_V2_AGENT=<name>` when invoking.

---

## Component B — Auto-Commit Daemon

This is a `launchd` service that wakes every 15 minutes and saves anything
dirty.

### B.1 — Inspect the plist (do NOT load yet)

```bash
cat /Users/kooshapari/CodeProjects/Phenotype/repos/_phenofleet-decisions/airlock-v2/daemons/com.phenotype.auto-commit-daemon.plist
```

Things to verify before loading:

- `ProgramArguments` points at the right python3 and script path.
- `EnvironmentVariables.AIRLOCK_V2_INTERVAL` matches your desired cadence (default 900s = 15min).
- `StandardOutPath`/`StandardErrorPath` writes go to a directory that
  already exists (the daemon auto-creates `~/.airlock-v2/logs/` on first
  run, but launchd creates the *file* lazily).
- `KeepAlive` is `true` so the daemon restarts after a crash.

### B.2 — One-time check before install

Run the daemon **once in foreground** to make sure it can find the repo
root and not crash:

```bash
AIRLOCK_V2_DRY_RUN=1 \
  python3 /Users/kooshapari/CodeProjects/Phenotype/repos/_phenofleet-decisions/airlock-v2/daemons/auto-commit-daemon.py --once
```

You should see log lines on stderr like
`{"ts": "2026-07-15T...", "level": "info", "msg": "sweep_start", ...}`. Press
Ctrl-C to exit if it loops; in `--once` mode it exits after one pass.

### B.3 — Install

```bash
cp /Users/kooshapari/CodeProjects/Phenotype/repos/_phenofleet-decisions/airlock-v2/daemons/com.phenotype.auto-commit-daemon.plist \
   ~/Library/LaunchAgents/
launchctl load -w ~/Library/LaunchAgents/com.phenotype.auto-commit-daemon.plist
launchctl list | grep com.phenotype.auto-commit-daemon
```

The PID printed should be a new long-running process.

### B.4 — Uninstall

```bash
launchctl bootout gui/$UID/com.phenotype.auto-commit-daemon \
  || launchctl unload ~/Library/LaunchAgents/com.phenotype.auto-commit-daemon.plist
rm ~/Library/LaunchAgents/com.phenotype.auto-commit-daemon.plist
```

---

## Component C — Cleanup Daemon

This is a heavier daemon that runs every 8 hours. It:

1. Merges every `wip/*` branch (created by the hook or auto-commit daemon)
   into a single `wip/<date>-consolidated` branch.
2. Force-pushes that consolidated branch to `origin` (using
   `--force-with-lease` for safety).
3. Deletes the source `wip/*` branches **only after** the consolidated branch
   is verified on origin.
4. Tarballs stale airlock v1 entries (≥30 days old) to
   `_phenofleet-decisions/airlock-cleanup/<id>.tar.zst`. **Never deletes the
   original entry** — that's a separate human-approved step.

### C.1 — Inspect

```bash
cat /Users/kooshapari/CodeProjects/Phenotype/repos/_phenofleet-decisions/airlock-v2/daemons/com.phenotype.cleanup-daemon.plist
```

The default interval is 28 800 seconds (8 hours). Adjust by setting
`cleanup-daemon.py --interval $((N*3600))` in the plist's `ProgramArguments`
to taste. **Caution:** setting `--interval` below 1 hour may overlap with
large wip branch sets and cause repeated merge conflicts.

### C.2 — Dry-run before install

```bash
AIRLOCK_V2_DRY_RUN=1 \
  python3 /Users/kooshapari/CodeProjects/Phenotype/repos/_phenofleet-decisions/airlock-v2/daemons/cleanup-daemon.py --once
```

Confirm it scans the repos without errors. Watch for
`consolidation_unhandled_exception` or `consolidation_done` log lines.

### C.3 — Install

```bash
cp /Users/kooshapari/CodeProjects/Phenotype/repos/_phenofleet-decisions/airlock-v2/daemons/com.phenotype.cleanup-daemon.plist \
   ~/Library/LaunchAgents/
launchctl load -w ~/Library/LaunchAgents/com.phenotype.cleanup-daemon.plist
launchctl list | grep com.phenotype.cleanup-daemon
```

### C.4 — Uninstall

```bash
launchctl bootout gui/$UID/com.phenotype.cleanup-daemon \
  || launchctl unload ~/Library/LaunchAgents/com.phenotype.cleanup-daemon.plist
rm ~/Library/LaunchAgents/com.phenotype.cleanup-daemon.plist
```

---

## Logs

All three components emit structured JSON-line logs to
`~/.airlock-v2/logs/`:

| Log file | Producer |
|---|---|
| `hook.log`         | `airlock-v2-hook.sh` |
| `auto-commit.log`  | `auto-commit-daemon.py` |
| `auto-commit.stdout.log` / `auto-commit.stderr.log` | `launchd` captures |
| `cleanup.log`      | `cleanup-daemon.py` |
| `cleanup.stdout.log` / `cleanup.stderr.log` | `launchd` captures |
| `smoke-hook.log`   | `airlock-v2-smoke-test.sh` (only when running smoke tests) |

Tail in real time:

```bash
tail -f ~/.airlock-v2/logs/auto-commit.log | jq -c '.'
tail -f ~/.airlock-v2/logs/cleanup.log | jq -c '.'
tail -f ~/.airlock-v2/logs/hook.log
```

---

## Reverting (full uninstall of all three components)

```bash
# 1. Stop the daemons.
launchctl bootout gui/$UID/com.phenotype.auto-commit-daemon 2>/dev/null \
  || launchctl unload ~/Library/LaunchAgents/com.phenotype.auto-commit-daemon.plist 2>/dev/null
launchctl bootout gui/$UID/com.phenotype.cleanup-daemon 2>/dev/null \
  || launchctl unload ~/Library/LaunchAgents/com.phenotype.cleanup-daemon.plist 2>/dev/null

# 2. Remove launchd plists.
rm -f ~/Library/LaunchAgents/com.phenotype.auto-commit-daemon.plist
rm -f ~/Library/LaunchAgents/com.phenotype.cleanup-daemon.plist

# 3. Remove the agent hook entries from settings.json/hooks.json/config.toml.
#    (Manual edit, by hand. The snippets shipped here are also reversible.)

# 4. (Optional) Remove all wip/* branches across repos to clean up after.
#    DESTRUCTIVE — only do this if you've verified the consolidated branches
#    exist on origin:
find ~/CodeProjects/Phenotype/repos -name ".git" -type d -prune -exec \
  sh -c 'cd "$0" && git branch --list "wip/*" -D' {} \;
```

---

## Safety summary

**Conservative (never happens automatically):**

- The daemons are not loaded automatically. The plists are inspectable.
- The auto-commit daemon does not delete any branch.
- The cleanup daemon only deletes wip/* branches it can prove are
  already in a verified consolidated branch on origin.
- The cleanup daemon does not delete `~/.airlock/repos/<id>`; only
  tarballs and writes a sidecar sha256.
- No edits to `~/.codex/`, `~/.claude/`, `~/.cursor/`, or `~/.airlock/`
  during install. You merge the hook configs by hand.

**Aggressive (every edit gets saved):**

- Every Codex/Claude edit tool call → `wip/<date>-<agent>-<event>` branch.
- Every 15 minutes, any repo with new dirty files → `wip/<date>-auto` branch.
- Every 8 hours, all `wip/*` branches are merged into a single
  `wip/<date>-consolidated` branch and force-pushed to origin.
- Every stale airlock v1 entry → `~/.phenofleet-decisions/airlock-cleanup/<id>.tar.zst`.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Auto-commit daemon exits with code 1 | `AIRLOCK_V2_ROOT` set to non-existent dir | unset or fix the env var |
| Hook script returns exit 2 | git not on PATH inside the agent's hook environment | ensure hook uses absolute `/usr/bin/env git` or pass `PATH=` via env |
| `consolidation_done` shows `remote_verified: false` | No network or origin is unreachable | check `git fetch origin` manually |
| Smoke test prints FAIL on the py_compile step | Python < 3.8 in PATH | Use `/usr/bin/python3` (this Mac's python3 is 3.13) |
| Many `wip/<date>-auto` branches pile up | Cleanup daemon is not installed | Install Cleanup Daemon (Component C) |
| LaunchAgent shows `status: not running` | Plist `KeepAlive` is fighting a crashing child | inspect `auto-commit.stderr.log` |

---

**End of install guide.**
