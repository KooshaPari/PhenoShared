# agent-orchestrator

Lane-based agent dispatch tool for coordinating parallel autonomous agents across non-overlapping file scopes.

## Quick Start (5 Minutes)

### 1. Build

```bash
cd tooling/agent-orchestrator
cargo build --release
```

### 2. Configure

Copy the example configuration:

```bash
cp orchestration.toml.example orchestration.toml
```

Edit `orchestration.toml` to define your lanes:
- **id:** Unique lane identifier
- **name:** Human-readable label
- **scope:** Non-overlapping glob patterns (e.g., `crates/focus-rules/**/*.rs`)
- **prompt_template:** Dispatch prompt for this lane
- **commit_message_prefix:** Git commit prefix (e.g., `rules:`)

### 3. Validate

```bash
cargo run -- lanes list
```

This lists all lanes and validates non-overlapping scopes.

### 4. Dispatch

Get the dispatch prompt for a lane:

```bash
cargo run -- lanes dispatch domain-state
```

Copy the prompt and dispatch to your agent.

### 5. Track Status

Monitor lane status:

```bash
cargo run -- lanes status
```

Shows in-flight lanes, coverage count, last dispatch time.

### 6. Audit Coverage

After N waves (~50 minutes), run an honest audit:

```bash
cargo run -- audit
```

Verifies all lanes are reachable and no files are orphaned.

## Subcommands

### `lanes list`

Lists all configured lanes with their scopes.

```
$ cargo run -- lanes list
Available Lanes (FocalPoint)

ID              Name                     Scope
================================================================================
domain-state    Domain & State           crates/focus-domain/**/*.rs, crates/...
connectors      Connectors & Integ.      crates/connector-*/**/*.rs
rules-rewards   Rules, Rewards & Pen.    crates/focus-rules/**/*.rs, ...
storage-sync    Storage & Sync           crates/focus-storage/**/*.rs, ...
audit-security  Audit & Security         crates/focus-audit/**/*.rs, crates/...
```

### `lanes dispatch <lane-id>`

Outputs a ready-to-copy dispatch prompt for the specified lane.

```
$ cargo run -- lanes dispatch connectors
=== AGENT DISPATCH PROMPT ===

Lane: connectors (Connectors & Integrations)
Files in scope: 18
Scope patterns: crates/connector-*/**/*.rs

PROMPT:

You are reviewing connector implementations (Canvas, Fitbit, GitHub, Strava, etc.).

Focus on:
1. Connector interface compliance
...

COMMIT MESSAGE PREFIX:
connector

FILES:
  crates/connector-canvas/src/lib.rs
  crates/connector-fitbit/src/lib.rs
  ...
```

### `lanes status`

Shows tracker status for all lanes (from `.orchestration-state.json`).

```
$ cargo run -- lanes status
Lane Status Report

Lane ID         In Flight       Coverage Count  Last Dispatch
========================================================
domain-state    No              3               2026-04-24T07:25...
connectors      No              2               2026-04-24T07:20...
rules-rewards   No              2               2026-04-24T07:15...
storage-sync    Yes             1               2026-04-24T07:10...
audit-security  No              1               2026-04-24T07:05...
```

### `audit`

Sweeps git log and verifies lane coverage:
- All lanes have matching files
- No orphaned files
- Commit prefix distribution
- File churn hotspots

```
$ cargo run -- audit
Audit: Lane Coverage Analysis

Project: FocalPoint
Repo root: .

Lane            Status
==================================================
domain-state    42 files
connectors      18 files
rules-rewards   33 files
storage-sync    56 files
audit-security  12 files

All lanes have matching files.
```

## Configuration (orchestration.toml)

```toml
project_name = "FocalPoint"
repo_root = "."
sweep_cadence_minutes = 5

[[lanes]]
id = "domain-state"
name = "Domain & State"
scope = [
    "crates/focus-domain/**/*.rs",
    "crates/focus-state-machine/**/*.rs",
]
prompt_template = "You are reviewing the domain and state machine layer..."
commit_message_prefix = "domain"
```

**Key constraints:**
- **Non-overlapping:** No file can match multiple lanes' scopes. Violation raises an error.
- **Glob patterns:** Standard glob syntax. Must match at least one file.
- **Commit prefix:** Should be 3–10 characters, lowercase, hyphen-separated.

## State File (`.orchestration-state.json`)

Created automatically. Tracks lane status:

```json
{
  "timestamp": "2026-04-24T07:30:00Z",
  "lanes": {
    "domain-state": {
      "lane_id": "domain-state",
      "last_dispatch": "2026-04-24T07:25:00Z",
      "in_flight": false,
      "last_commit_sha": "abc123...",
      "coverage_count": 3
    }
  }
}
```

**Fields:**
- `in_flight` — true if lane dispatch is pending.
- `coverage_count` — number of successful waves.
- `last_commit_sha` — most recent commit from this lane.

## Dispatch Workflow (5-Minute Cadence)

1. **T+0min:** Run `lanes list` to show available lanes.
2. **T+1min:** Run `lanes dispatch domain-state` to get the prompt.
3. **T+2min:** Dispatch prompt to agent 1 (domain-state).
4. **T+2min:** Run `lanes dispatch connectors` to get the next prompt.
5. **T+3min:** Dispatch prompt to agent 2 (connectors).
6. **Repeat** for remaining lanes in parallel (agents work independently).
7. **T+5min:** Run `lanes status` to confirm all agents have completed.
8. **T+5min:** Run `lanes dispatch domain-state` again for wave 2 (agent 1).
9. **Repeat** sweeps every 5 minutes.
10. **T+50min:** Run `audit` to verify coverage across all lanes.

## Non-Overlapping Algorithm

The tool validates scopes before any dispatch:

```
for each lane:
  for each glob pattern:
    expand glob
    check for conflicts with other lanes
```

**Example error:**
```
Error: File 'crates/focus-rules/src/lib.rs' is claimed by both
lane 'rules-rewards' and lane 'shared-eval'. Scopes must be non-overlapping.
```

**Fix:** Edit orchestration.toml and adjust glob patterns until each file is claimed by exactly one lane.

## Testing

```bash
cargo test
```

Tests cover:
- Lane parsing from TOML
- Non-overlap detection (errors on conflict)
- Tracker state serialization (JSON round-trip)
- Glob expansion and file matching

## Reference

- **Patterns & Motivation:** `docs/engineering/agent_orchestration_patterns.md`
- **Example Config:** `orchestration.toml.example` (copy and edit)
- **CLI Help:** `cargo run -- --help`

## When to Use

**Good for:**
- 2–8 agents on the same codebase
- Well-modularized structure (clear lane boundaries)
- 5–10 minute feedback loops acceptable
- Want auditable, prefix-tagged commit history

**Not for:**
- Single agent (simpler tools exist)
- Tightly coupled code (hard to define non-overlapping lanes)
- Sub-minute coordination required
