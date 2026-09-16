# forge — host-side monitoring scripts

These scripts implement the three `com.phenoforge.forge-*` launchd
agents declared by the WBS-PERT-100 v0.12 Phase 3 tasks 36-50.

## Scripts (v0.12 phase 3, status|check|report contract)

| Script | Subcommands | Purpose | launchd plist |
|--------|-------------|---------|---------------|
| `forge-watchdog.sh`  | `status`, `check`, `report` | Disk + memory + process count monitoring | `com.phenoforge.forge-watchdog` |
| `forge-net-heal.sh`  | `status`, `check`, `report` | DNS + TCP reachability to 13 critical endpoints | `com.phenoforge.forge-net-heal` |
| `forge-proc-reap.sh` | `status`, `reap`,   `report` | Zombie reap + worktree lock cleanup | `com.phenoforge.forge-proc-reap` |

The `check` (and `reap` for proc-reap) sub-command is the default
invoked by the launchd plists.

> `forge-proc-reaper.sh` (with the `-er` suffix) is **deprecated**.
> It is preserved at host-side `~/.forge/bin/` for backwards
> compatibility but is no longer referenced by any plist.

## Subcommand contracts

### `forge-watchdog.sh`

| Subcommand | Behavior | Exit |
|------------|----------|------|
| `status`   | Print disk/mem/proc stats in human-readable form | 0 |
| `check`    | Emit one JSON `{level,msg}` line per threshold breach; exit 1 if disk >= 95%, mem used >= 90%, procs > 1000 | 0 = healthy, 1 = degraded |
| `report`   | Dump a markdown summary table | 0 |

### `forge-net-heal.sh`

| Subcommand | Behavior | Exit |
|------------|----------|------|
| `status`   | List 5 DNS hosts + 8 TCP endpoints with live probe status | 0 |
| `check`    | Probe all hosts; exit 0 if all reachable, exit 1 if any fail | 0 = all OK, 1 = at least 1 fail |
| `report`   | Markdown table of last `check` (cached in `${HOME}/.pheno-harness/state/forge-net-heal.last`) | 0 |

5 critical DNS hosts: `github.com`, `pypi.org`, `anthropic.com`,
`openai.com`, `huggingface.co`.

8 critical TCP endpoints: `1.1.1.1:443`, `8.8.8.8:53`,
`github.com:443`, `pypi.org:443`, `anthropic.com:443`,
`openai.com:443`, `huggingface.co:443`, `1.0.0.1:53`.

### `forge-proc-reap.sh`

| Subcommand | Behavior | Exit |
|------------|----------|------|
| `status`   | List zombies, active worktrees, and orphaned `.git/index.lock` files | 0 |
| `reap`     | SIGCHLD parent of zombies >= 60min old; remove orphaned `.git/index.lock` files | 0 = nothing, 1 = at least 1 action |
| `report`   | Markdown summary of last `reap` | 0 |

## Install location

The launchd plists hard-code the install path as
`/Users/kooshapari/.forge/bin/`. To install from a clean checkout:

```sh
mkdir -p ~/.forge/bin
cp scripts/forge/forge-watchdog.sh scripts/forge/forge-net-heal.sh scripts/forge/forge-proc-reap.sh ~/.forge/bin/
chmod +x ~/.forge/bin/forge-{watchdog,net-heal,proc-reap}.sh
```

## Exit codes

All three scripts follow the convention:

- `0` = healthy / no action required
- `1` = degraded / action required (zombies reaped, heal attempted,
  resource warning surfaced)
- `2` = invocation error (bad subcommand)

## Logging

All scripts write timestamped log lines via `printf` to launchd's
`StandardOutPath`. The launchd plists route stdout/stderr to
`~/.pheno-harness/logs/com.phenoforge.<label>.{log,err}`.

`forge-net-heal.sh` and `forge-proc-reap.sh` additionally write a
last-state snapshot to `~/.pheno-harness/state/forge-<label>.last`
so that `report` can render a stable table even between launches.

## Schedule

| Job | RunAtLoad | KeepAlive | StartInterval |
|-----|-----------|-----------|---------------|
| forge-watchdog | false | false | (kickstart only) |
| forge-net-heal | false | false | 3600 sec (1h) |
| forge-proc-reap | false | false | 1800 sec (30m) |

The forge-watchdog runs only on demand (kickstart). forge-net-heal
and forge-proc-reap are scheduled at 1h and 30m intervals
respectively.

## Verification

After install, force-fire each agent:

```sh
UID_VAL=$(id -u)
launchctl kickstart -k gui/$UID_VAL/com.phenoforge.forge-watchdog
launchctl kickstart -k gui/$UID_VAL/com.phenoforge.forge-net-heal
launchctl kickstart -k gui/$UID_VAL/com.phenoforge.forge-proc-reap
tail -5 ~/.pheno-harness/logs/com.phenoforge.forge-watchdog.log
tail -5 ~/.pheno-harness/logs/com.phenoforge.forge-net-heal.log
tail -5 ~/.pheno-harness/logs/com.phenoforge.forge-proc-reap.log
```

Expected (healthy):

```
[2026-...Z] watchdog check: disk=NN% mem=NN% procs=NNN
[2026-...Z] watchdog: healthy (disk=NN%, mem=NN%, procs=NNN)
[2026-...Z] net-heal check: starting (5 DNS, 8 TCP)
[2026-...Z] net-heal: all endpoints reachable
[2026-...Z] proc-reap: nothing to reap
```
