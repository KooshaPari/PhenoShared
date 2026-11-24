# CRON_OPS.md — launchd cron operations runbook

This runbook covers the four `com.phenotype.pheno-harness.*` launchd agents
installed by `scripts/cron/install_launchd.sh`. It is **non-LLM host engineering**
only — it documents how to observe, debug, and maintain the local cron schedule.

## The four agents

| Label                                          | Schedule              | Wrapper script                                | Purpose                                 |
| ---------------------------------------------- | --------------------- | --------------------------------------------- | --------------------------------------- |
| `com.phenotype.pheno-harness.sota-snapshot`    | daily 04:00 UTC       | `scripts/cron/snapshot_sota.py`               | write today's SOTA snapshot + SHA      |
| `com.phenotype.pheno-harness.health-repo`      | Mon 03:00 UTC         | `scripts/cron/health_repo_cron.sh`            | repo health probe + drift gate         |
| `com.phenotype.pheno-harness.worktree-gc`     | Wed 04:00 UTC         | `scripts/cron/worktree_gc_cron.sh`            | prune gone branches + worktrees        |
| `com.phenotype.pheno-harness.lint-branches`   | Fri 04:00 UTC         | `scripts/cron/lint_branches_cron.sh`          | 8-prefix branch taxonomy lint           |

LaunchAgent weekday convention: `0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat`.
Schedules above match this convention; `*-branches` is `Fri=5`, not "this Friday".

## Observability

### Where logs land

```
~/.pheno-harness/logs/
  com.phenotype.pheno-harness.sota-snapshot.{log,err}
  com.phenotype.pheno-harness.health-repo.{log,err}
  com.phenotype.pheno-harness.worktree-gc.{log,err}
  com.phenotype.pheno-harness.lint-branches.{log,err}
```

Per-agent output dirs (created on first run):

```
bench/results/sota/<YYYY-MM-DD>/snapshot.json + snapshot.sha256
bench/results/health_repo/<YYYY-MM-DD>/
bench/results/gc/<YYYY-MM-DD>/
bench/results/branch-lint/<YYYY-MM-DD>/
```

### Quick status commands

```sh
# All 4 agents loaded?
launchctl list 2>/dev/null | grep com.phenotype.pheno-harness

# Per-agent next-run + last-exit
for a in sota-snapshot health-repo worktree-gc lint-branches; do
  launchctl print "gui/$(id -u)/com.phenotype.pheno-harness.$a" \
    | grep -iE "next run|last exit|interval|weekday|hour|minute" \
    | head -5
done

# Most recent log line per agent
for a in sota-snapshot health-repo worktree-gc lint-branches; do
  tail -1 "~/.pheno-harness/logs/com.phenotype.pheno-harness.$a.log"
done
```

## Common operations

### Bootstrap all 4 (idempotent)

```sh
for a in sota-snapshot health-repo worktree-gc lint-branches; do
  launchctl bootstrap "gui/$(id -u)" \
    "$HOME/Library/LaunchAgents/com.phenotype.pheno-harness.$a.plist"
done
```

`launchctl bootstrap` is idempotent — "already loaded" errors are silent.

### Force-fire an agent right now (without waiting for schedule)

```sh
launchctl kickstart -k "gui/$(id -u)/com.phenotype.pheno-harness.<name>"
```

Useful for verifying a .sh wrapper fix without waiting for the next scheduled fire.

### Unload an agent

```sh
launchctl bootout "gui/$(id -u)/com.phenotype.pheno-harness.<name>"
```

The .plist stays on disk; the agent is just de-registered from launchd until
next `bootstrap` (or system reboot).

### Re-install (after a script edit)

The plists are generated from `scripts/cron/install_launchd.sh` (do NOT edit
the .plist files directly — they'll drift on next re-install). To rebuild:

```sh
cd <repo-root>
bash scripts/cron/install_launchd.sh install 4
```

This rewrites all 4 plists and bootstraps them. The previous load stays valid
because `launchctl bootstrap` is idempotent.

## Common failure modes

### Agent fires but exits non-zero

Look at `~/.pheno-harness/logs/com.phenotype.pheno-harness.<name>.err` — the
stderr from the wrapper script. Common causes:

1. **Disk full** — the wrapper can't write the snapshot. Fix: `df -h /`
2. **Outdated wrapper path** — the plist references `scripts/cron/<name>.sh`
   but the script was deleted/moved. Fix: `ls scripts/cron/<name>.sh`
3. **CWD issues** — the wrapper assumes cwd is the repo root. The plist's
   `WorkingDirectory` is set to `${SCRIPT_DIR}/../..` which is the repo root.

### Agent doesn't fire at all

Check `next run` in `launchctl print`:

```sh
launchctl print "gui/$(id -u)/com.phenotype.pheno-harness.sota-snapshot" \
  | grep "next run"
```

If `next run` is `never` or `none`, the plist has a malformed schedule (e.g.
`Weekday: 7` instead of `5`, which is `Sat` not `Fri`). Re-install.

### "Bootstrap failed: 5: I/O error"

Either:
- The agent is already loaded (re-run `bootstrap` and it silently succeeds), or
- The .plist file is malformed (`plutil -lint <plist>` to verify)

### plist points to a deleted script

```sh
ls scripts/cron/<name>.sh        # confirm script exists
plutil -p ~/Library/LaunchAgents/com.phenotype.pheno-harness.<name>.plist | head
```

If the plist's `ProgramArguments` second entry points to a missing file, the
launchd error is silent on subsequent fires. Re-install via
`install_launchd.sh install 4`.

## Why "set -f" matters in install_launchd.sh

The plist template uses literal `*` (the daily-schedule sentinel) inside the
`StartCalendarInterval` dict. Without `set -f`, bash's pathname expansion
turns `*` into the cwd's alphabetically-sorted filenames — for a sota-snapshot
agent launched from `~/CodeProjects/Phenotype/repos/pheno-harness`, that
meant `Weekday: AGENTS.md`, `Hour: agileplus-specs`, `Minute: bench`. The
plist loaded without error; the schedule silently wrong.

`set -f` at the top of `install_launchd.sh` disables globbing so the literal
`*` survives the heredoc unchanged. This is the #1 source of cron mystery
failures in this repo; do not remove it.

## SOTA snapshot chain

The cron writes a daily `bench/results/sota/<YYYY-MM-DD>/snapshot.json` plus
a `<...>/snapshot.sha256` sidecar. The sidecar is **force-added** in every
commit that captures a new day (because `bench/results/**` is gitignored).

The chain lets downstream consumers (CI, audits) verify integrity by
re-hashing the .json file and comparing to the .sha256.

If a date is missing from `bench/results/sota/`, check `~/.pheno-harness/logs/
com.phenotype.pheno-harness.sota-snapshot.err` for the failure mode. Common
causes:

- **Disk full** (the snapshot write partially completed; both .json and
  .sha256 are present but the .json is incomplete)
- **Plist path broken** (script path was wrong; .err says `No such file or directory`)
- **Cron misfire** (the launchd was paused — `launchctl print` would show
  `state: not running` for that day)

To backfill a missing date manually (skip if the launchd is the canonical
source for that day):

```sh
cd <repo-root>
python3 scripts/cron/snapshot_sota.py
# then force-add the sidecar:
git add -f bench/results/sota/<YYYY-MM-DD>/snapshot.sha256
git commit -m "chore(snapshot): backfill <YYYY-MM-DD> SOTA snapshot"
```

The `--backfill` flag is an explicit alternative to the implicit backfill
that `--date <YYYY-MM-DD>` enables. Use it when you want to force
`evidence_label='backfilled'` regardless of `--live`:

```sh
# Explicit backfill — forces evidence_label='backfilled' even if --live is set
python3 scripts/cron/snapshot_sota.py --date 2026-07-25 --backfill \\
    --backfill-note "forensic gap from audit close-out"
```

## Cross-platform note

The macOS launchd agent is the **local-only** schedule. For the equivalent
upstream-CI schedule (linux x86_64, GitHub Actions runners), use:

- `.github/workflows/sota-snapshot.yml` (daily 04:30 UTC, ubuntu-latest)
- `.github/workflows/metal-kernel-fuzz.yml` (probe-only on push + weekly
  OFB on macos-13)

Both shipped in commit `cf318e4`. They complement the local cron: launchd
fires at 04:00, CI fires at 04:30 (avoids races).

For WSL/Fedora dual-GPU hosts (no Metal), the equivalent cron jobs live in
`/etc/cron.d/pheno-harness/` or systemd timers; the script payloads are
identical to the macOS wrappers, just `/bin/bash` instead of `/bin/zsh`.
