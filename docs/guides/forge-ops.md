# Forge ops runbook — pheno-harness

**Date:** 2026-08-12 (v0.14 Phase 3 task 49)

This runbook covers day-2 operations for the three `com.phenoforge.forge-*`
LaunchAgents: `forge-watchdog`, `forge-net-heal`, `forge-proc-reap`.

## Quick status

```bash
bash scripts/forge_status.sh
```

| Column | Meaning |
|--------|---------|
| `PID` | process id (or `(on demand)` for non-periodic agents) |
| `EXIT` | last-exit code (or `(on demand)`) |
| `NEXT-RUN` | next scheduled run (or `(on demand)`) |
| `LAST-LOG` | tail of `~/.pheno-harness/logs/<label>.log` |

Exit codes: `0 = all loaded`, `2 = partial`, `3 = unloadable`,
`1 = usage error`.

## Per-agent runbook

### forge-watchdog

**Purpose:** Reports degraded host state (disk, mem, processes).

**Logs:** `~/.pheno-harness/logs/com.phenoforge.forge-watchdog.log`

**Common failures:**

| Log | Likely cause | Fix |
|-----|--------------|-----|
| `watchdog: degraded (disk=99%+, mem=99%+, procs=600+)` | host resource pressure | `docker system prune` + restart peers; ping #phenotype-ops |
| `watchdog: ok (disk=N%, ...)` | nominal | — |

**Manual run:**

```bash
zsh -c ~/.forge/bin/forge-watchdog.sh
```

### forge-net-heal

**Purpose:** Probes net endpoints (configured in launchd plist env).

**Logs:** `~/.pheno-harness/logs/com.phenoforge.forge-net-heal.log`

**Common failures:**

| Log | Likely cause | Fix |
|-----|--------------|-----|
| `net-heal: all endpoints reachable` | nominal | — |
| `net-heal: unreachable N endpoints` | routing or DNS issue | `curl -v https://tracera.phenotype.local/health` then file ticket |

**Manual run:**

```bash
zsh -c ~/.forge/bin/forge-net-heal.sh
```

### forge-proc-reap

**Purpose:** Cleans up orphaned subprocesses leaked by prior runs.

**Logs:** `~/.pheno-harness/logs/com.phenoforge.forge-proc-reap.log`

**Common failures:**

| Log | Likely cause | Fix |
|-----|--------------|-----|
| `proc-reap: nothing to reap` | nominal | — |
| `proc-reap: reaped N processes` | leakage happened | investigate the parent process; ticket #phenotype-ops |

**Manual run:**

```bash
zsh -c ~/.forge/bin/forge-proc-reap.sh
```

## Idempotency

Every script is safe to re-run; each writes a new line to its log
on every execution.

## Reinstall

```bash
# 1. Re-install the 4 LaunchAgents (sota-snapshot + 3 forge-*)
bash scripts/cron/install_launchd.sh install 4

# 2. Verify
bash scripts/forge_status.sh

# 3. Force-fire the agents to confirm exec paths
launchctl kickstart -k gui/$(id -u)/com.phenoforge.forge-watchdog
launchctl kickstart -k gui/$(id -u)/com.phenoforge.forge-net-heal
launchctl kickstart -k gui/$(id -u)/com.phenoforge.forge-proc-reap

# 4. Re-check logs
tail -1 ~/.pheno-harness/logs/com.phenoforge.forge-*.log
```

## Uninstall

```bash
# Stop the agents
launchctl bootout gui/$(id -u)/com.phenoforge.forge-watchdog 2>/dev/null
launchctl bootout gui/$(id -u)/com.phenoforge.forge-net-heal 2>/dev/null
launchctl bootout gui/$(id -u)/com.phenoforge.forge-proc-reap 2>/dev/null

# Confirm
bash scripts/forge_status.sh
# Expect exit code 2 (partial / unloaded)
```

## Acceptance

ac_v1: this runbook on `main` with DAG id `v0.14-task-49` in footer.

Refs: v0.14-task-49, scripts/forge_status.sh.
