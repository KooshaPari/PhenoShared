#!/usr/bin/env python3
"""Generate static HTML dashboard for resume-all + multi-repo backlog.

Writes a self-contained HTML file with:
- Cockpit tick (last health-check + status)
- Per-repo progress bars
- Per-epic/goal DAG tree progress bars (intra-repo)
- Per-overall cross-repo progress
- Hash-based filename so many agents regenerating produce stable name when content matches
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

# ---------- Config ----------
HANDOFF = Path("/Users/kooshapari/handoff/2026-08-05-crash-recovery-handoff.md")
DASHBOARD_DIR = Path("/Users/kooshapari/.local/share/resume-all/dashboards")
DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
HEALTH_FILE = Path("/Users/kooshapari/.local/share/resume-all/health.txt")
DATA_FILE = DASHBOARD_DIR / "cockpit-data.json"

# ---------- Health tick ----------
def get_health_tick():
    """Read health.txt and return (timestamp, status)."""
    if not HEALTH_FILE.exists():
        return dt.datetime.now(dt.timezone.utc).isoformat(), "UNKNOWN"
    text = HEALTH_FILE.read_text()
    # First line: "resume-all health check -- 2026-08-08 16:37:18"
    # Last status line: "Overall:           HEALTHY  (...)"
    status = "UNKNOWN"
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
    for line in text.splitlines():
        if line.startswith("resume-all health check"):
            ts = line.split("--", 1)[-1].strip()
            try:
                d = dt.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                timestamp = d.replace(tzinfo=dt.timezone.utc).isoformat()
            except ValueError:
                pass
        elif line.startswith("Overall:"):
            parts = line.split(":", 1)[-1].strip().split()
            if parts:
                status = parts[0]
    return timestamp, status


def count_assets():
    """Count launchd jobs, bin scripts, crates, etc."""
    plists = list(Path("/Users/kooshapari/Library/LaunchAgents").glob("com.kooshapari.*.plist"))
    bin_scripts = list(Path("/Users/kooshapari/bin").glob("*.py")) + \
                  list(Path("/Users/kooshapari/bin").glob("*-wrapper"))
    crates = [d.name for d in Path("/Users/kooshapari/thegent/crates").iterdir()
              if d.is_dir() and not d.name.startswith("_")]
    configs = list(Path("/Users/kooshapari/.config/resume-all").glob("*.toml")) if Path("/Users/kooshapari/.config/resume-all").exists() else []
    return {
        "launchd_jobs": len(plists),
        "bin_scripts": len(bin_scripts),
        "rust_crates": len(crates),
        "crates": len(crates),
        "crates_list": sorted(crates),
        "configs": len(configs),
        "config_list": sorted([c.name for c in configs]),
        "plists_list": sorted([p.name for p in plists]),
    }


# ---------- Repos ----------
def load_sentiment_buckets():
    """Run sentiment-sessions.py --histogram and parse the bucket counts."""
    import subprocess
    try:
        r = subprocess.run(
            ["/Users/kooshapari/bin/sentiment-sessions.py", "--histogram"],
            capture_output=True, text=True, timeout=30,
        )
        buckets = {"great": 0, "good": 0, "neutral": 0, "concerning": 0, "bad": 0}
        for line in r.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] in buckets:
                try:
                    buckets[parts[0]] = int(parts[1])
                except (ValueError, IndexError):
                    pass
        return buckets
    except (subprocess.TimeoutExpired, OSError):
        return {"great": 0, "good": 0, "neutral": 0, "concerning": 0, "bad": 0}


def load_telemetry_latest():
    """Read the last telemetry tick."""
    tel = Path("/Users/kooshapari/.local/share/resume-all/telemetry.ndjson")
    if not tel.exists():
        return None
    lines = tel.read_text().splitlines()
    for line in reversed(lines):
        line = line.strip()
        if not line: continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def get_bridge_health_latest():
    """Read the latest cross-host bridge health tick (NDJSON)."""
    health = Path("/Users/kooshapari/.local/share/resume-all/bridge-health.ndjson")
    if not health.exists():
        return None
    lines = health.read_text().splitlines()
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def get_tailscale_watch_latest():
    """Read the latest tailscale-watch tick (NDJSON).

    Returns dict with state (up/down), daemon_pid_running, has_tailscale_routes,
    status_exit_code, host_lines, ts_iso. None if file absent.
    """
    ts = Path("/Users/kooshapari/.local/share/resume-all/tailscale-watch.ndjson")
    if not ts.exists():
        return None
    lines = ts.read_text().splitlines()
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def get_bridge_history_summary(max_ticks=24):
    """Read the last N ticks of bridge-history.ndjson and compute summary stats.

    Returns dict with:
      - total_ticks: int
      - healthy_count: int
      - unhealthy_count: int
      - uptime_pct: float
      - last_24_states: list[bool] (most-recent first)
      - latest_rows_per_host: dict[str, int]
    Returns None if file absent.
    """
    bh = Path("/Users/kooshapari/.local/share/resume-all/bridge-history.ndjson")
    if not bh.exists():
        return None
    lines = bh.read_text().splitlines()
    parsed = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not parsed:
        return None
    # Take last max_ticks
    parsed = parsed[-max_ticks:]
    healthy = sum(1 for t in parsed if str(t.get("bridge_healthy", "")).lower() == "true")
    unhealthy = len(parsed) - healthy
    uptime_pct = (healthy / len(parsed) * 100.0) if parsed else 0.0
    last_states = [str(t.get("bridge_healthy", "")).lower() == "true" for t in parsed]
    # Latest rows-per-host (from most recent tick)
    latest_rows = {}
    if parsed:
        for h in parsed[-1].get("hosts", []):
            latest_rows[h.get("host", "?")] = h.get("rows", 0)
    return {
        "total_ticks": len(parsed),
        "healthy_count": healthy,
        "unhealthy_count": unhealthy,
        "uptime_pct": uptime_pct,
        "last_states": last_states,  # oldest→newest
        "latest_rows_per_host": latest_rows,
    }


def get_cross_host_snapshot():
    """Read the live cross-host snapshot (Phase B bridge output).

    Scans ~/.local/share/resume-all/*.snapshot.jsonl for files with actual rows.
    Returns: dict with per-host stats (rows, harnesses, cwds, age_seconds, last_pull_ts).
    Skips placeholder/empty/stale files that don't have meaningful data.
    """
    snap_dir = Path("/Users/kooshapari/.local/share/resume-all")
    hosts = {}
    now = dt.datetime.now(dt.timezone.utc)
    for snap_file in sorted(snap_dir.glob("*.snapshot.jsonl")):
        host = snap_file.name.replace(".snapshot.jsonl", "")
        # Skip placeholder names (bad CLI invocations, IPs, etc.)
        if host.startswith("--") or host.startswith(".") or "/" in host:
            continue
        if not host or host[0].isdigit():
            # Skip pure-IP hostnames or empty names (likely placeholder)
            continue
        try:
            stat = snap_file.stat()
            # Skip 0-byte placeholders (no live data)
            if stat.st_size < 100:
                continue
            mtime = dt.datetime.fromtimestamp(stat.st_mtime, tz=dt.timezone.utc)
            age = (now - mtime).total_seconds()
            # Skip files older than 24h (irrelevant)
            if age > 86400:
                continue
            text = snap_file.read_text(errors="replace")
            rows = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            harnesses = set(r.get("harness", "?") for r in rows)
            cwds = set(r.get("cwd", "?") for r in rows if r.get("cwd"))
            hosts[host] = {
                "rows": len(rows),
                "bytes": stat.st_size,
                "harnesses": sorted(harnesses),
                "harness_count": len(harnesses),
                "cwd_count": len(cwds),
                "with_session_id": sum(1 for r in rows if r.get("session_id")),
                "mtime_iso": mtime.isoformat(),
                "age_seconds": int(age),
                "stale": age > 180,  # > 3min = stale
            }
        except Exception as e:
            # Silently skip unreadable files
            continue
    return hosts


def load_phenotype_audit():
    """Load the Phenotype sub-repo audit JSONs (from worker output)."""
    audit_dir = Path("/Users/kooshapari/CodeProjects/Phenotype/repos/.cockpit-audit")
    if not audit_dir.exists():
        return []
    sub_repos = []
    for jf in sorted(audit_dir.glob("*.json")):
        try:
            d = json.loads(jf.read_text())
            sub_repos.append(d)
        except (OSError, ValueError):
            continue
    return sub_repos


def phenotype_data():
    sub_repos = load_phenotype_audit()
    total_sub = len(sub_repos)
    total_prs = sum(len(r.get("open_prs", [])) for r in sub_repos)
    total_issues = sum(len(r.get("open_issues", [])) for r in sub_repos)
    total_todos = sum(r.get("todo_count", 0) for r in sub_repos)
    total_findings = sum(r.get("audit_findings", 0) for r in sub_repos)
    total_worktrees = sum(r.get("worktrees", 0) for r in sub_repos)

    # Build sub-repo rows
    sub_rows = ""
    if sub_repos:
        # Sort by 30d commits desc
        for r in sorted(sub_repos, key=lambda x: -int(x.get("commit_count_30d", 0))):
            commits = r.get("commit_count_30d", 0)
            todos = r.get("todo_count", 0)
            findings = r.get("audit_findings", 0)
            worktrees = r.get("worktrees", 0)
            branch = r.get("branch", "main")
            date = r.get("last_commit_date", "")[:10]
            last_commit = r.get("last_commit", "")[:60]
            todo_color = "#f59e0b" if todos > 0 else "#10b981"
            findings_color = "#ef4444" if findings > 50 else "#f59e0b" if findings > 0 else "#10b981"
            sub_rows += f'''
              <tr>
                <td><strong>{r["name"]}</strong></td>
                <td style="font-family:monospace;font-size:0.85em;">{branch}</td>
                <td style="text-align:center;">{date}</td>
                <td style="text-align:center;color:#93c5fd;font-weight:bold;">{commits}</td>
                <td style="text-align:center;color:{todo_color};">{todos}</td>
                <td style="text-align:center;color:{findings_color};">{findings}</td>
                <td style="text-align:center;">{worktrees}</td>
                <td style="font-family:monospace;font-size:0.8em;opacity:0.7;">{last_commit}…</td>
              </tr>'''

    return {
        "name": "Phenotype",
        "summary": f"Phenotype monorepo with {total_sub} sub-repos, {total_prs} open PRs, {total_issues} open issues, {total_worktrees} worktrees, {total_todos} TODOs, {total_findings} audit findings",
        "epics": [
            {"name": "cockpit render harness", "status": "done", "progress_pct": 100, "goals": [{"name": "_airlock-cockpit-render.py (23.9 KB)", "status": "done"}]},
            {"name": "deterministic verifier", "status": "done", "progress_pct": 100, "goals": [{"name": "_test_deterministic_verifier.py (5 KB)", "status": "done"}]},
            {"name": "airlock recovery waves 1-9", "status": "done", "progress_pct": 100, "goals": [{"name": "124.62 GiB reclaimed across 9 waves", "status": "done"}]},
            {"name": "sub-repo activity (cockpit-audit)", "status": "in_progress", "progress_pct": 80,
             "goals": [
                 {"name": f"{total_sub} sub-repos audited", "status": "done"},
                 {"name": f"{total_prs} open PRs tracked", "status": "done"},
                 {"name": f"{total_todos} TODOs aggregated", "status": "done"},
                 {"name": "Top active: " + ", ".join(r["name"] for r in sorted(sub_repos, key=lambda x: -int(x.get("commit_count_30d", 0)))[:3]),
                  "status": "done"},
             ]},
        ],
        "sub_repos_table": sub_rows if sub_rows else None,
        "backlog": [
            {"task": f"Triage {total_todos} TODOs across {total_sub} sub-repos", "priority": 1, "effort_h": 4.0, "blocked_by": []},
            {"task": f"Address {total_findings} audit findings (top 5)", "priority": 2, "effort_h": 8.0, "blocked_by": []},
            {"task": f"Review {total_prs} open PRs across sub-repos", "priority": 3, "effort_h": 2.0, "blocked_by": []},
            {"task": "Consolidate sub-repos with WORKTREE pattern", "priority": 4, "effort_h": 8.0, "blocked_by": []},
        ],
    }


def resume_all_data():
    """Build the resume-all repo data."""
    return {
        "name": "resume-all",
        "summary": "Crash-recovery toolkit for Ghostty/winterm across 5+ harnesses (forge/codex/cursor/kilo/droid/opencode)",
        "epics": [
            {
                "name": "Phase A — Polish",
                "status": "done",
                "progress_pct": 100,
                "goals": [
                    {"name": "Core scripts shipped (session_snapshot, resume-all, resume-cross)", "status": "done"},
                    {"name": "Patched detect_backend()", "status": "done"},
                    {"name": "Snapshot walker timeout 10s→3s", "status": "done"},
                ],
            },
            {
                "name": "Phase B — Multi-platform (WSL/Windows/Linux)",
                "status": "in_progress",
                "progress_pct": 60,
                "goals": [
                    {"name": "Tailscale SSH bridge pattern (desk→WSL Fedora)", "status": "done"},
                    {"name": "resume-bridge walker pulled 94 rows from WSL Fedora", "status": "done"},
                    {"name": "Py 3.14 dataclass + importlib fix", "status": "done"},
                    {"name": "WezTerm backend in detect_backend()", "status": "pending", "effort_h": 4},
                    {"name": "Windows backend (named pipes, tasklist walker)", "status": "pending", "effort_h": 8},
                    {"name": "Cross-host resume (open WezTerm on Windows from macOS trigger)", "status": "in_progress", "effort_h": 6},
                    {"name": "Smoke test resume-bridge against cachyos + WSL Fedora E2E", "status": "pending", "effort_h": 2},
                ],
            },
            {
                "name": "Phase C — ShareCLI IPC",
                "status": "done",
                "progress_pct": 100,
                "goals": [
                    {"name": "IPC daemon (sharecli-ipc-daemon) NDJSON v0.2.0", "status": "done"},
                    {"name": "IPC bridge for cross-platform", "status": "done"},
                    {"name": "Tray app (sharecli-tray) with menu actions", "status": "done"},
                    {"name": "Spawn thegent-mcp as child process", "status": "done"},
                ],
            },
            {
                "name": "Phase D — MCP server",
                "status": "done",
                "progress_pct": 100,
                "goals": [
                    {"name": "thegent-mcp with 7 tools + 4 resources", "status": "done"},
                    {"name": "JSON-RPC 2.0 with notification suppression", "status": "done"},
                    {"name": "Wired to Cursor + Claude + Codex (3 clients)", "status": "done"},
                ],
            },
            {
                "name": "Phase E — Session manager features",
                "status": "in_progress",
                "progress_pct": 85,
                "goals": [
                    {"name": "E07 dependencies.toml + dependency-watch daemon", "status": "done"},
                    {"name": "E10 bookmarks + --only filter (25 tests)", "status": "done"},
                    {"name": "E11 workspaces + --workspace flag (31 tests)", "status": "done"},
                    {"name": "E12 rank-sessions.py (25 tests, 7 weighted components)", "status": "done"},
                    {"name": "E13 voice-activate (audio capture + VAD + simulate)", "status": "done"},
                    {"name": "E14 workspace-templates (17 tests, 4 built-ins)", "status": "done"},
                    {"name": "E15 voice polish (stats/history/loop)", "status": "done"},
                    {"name": "E08-E09 (sentiment, telemetry)", "status": "pending", "effort_h": 8},
                ],
            },
            {
                "name": "Phase F — Production hardening",
                "status": "done",
                "progress_pct": 100,
                "goals": [
                    {"name": "F02 crash-forensic.py (32.6 KB)", "status": "done"},
                    {"name": "F05 leak-detect.py (42.9 KB, 17 tests)", "status": "done"},
                    {"name": "F06 fuzz-test.py (0 crashes across 56 inputs)", "status": "done"},
                    {"name": "F07 health-check.py (supports periodic jobs)", "status": "done"},
                    {"name": "F09 SLA monitor (38.1 KB, 13 tests)", "status": "done"},
                    {"name": "F10 monthly DR drill + automation", "status": "done"},
                    {"name": "F11 RUNBOOK.md (439 lines)", "status": "done"},
                    {"name": "F12 canary-runner (8 tests, 5-min poll)", "status": "done"},
                    {"name": "F13 flag-tray-bridge (8/9 tests, 30s poll)", "status": "done"},
                    {"name": "F14 incident-respond (6/6 tests) + ipc-recover fallback", "status": "done"},
                    {"name": "F15 postmortem (7/7 tests, canary targets)", "status": "done"},
                ],
            },
        ],
        "backlog": [
            {"task": "Visual click-through of MCP+tray in live Cursor UI", "priority": 1, "effort_h": 0.5, "blocked_by": ["requires human at Mac"]},
            {"task": "Verify mTLS end-to-end with real IPC traffic", "priority": 2, "effort_h": 1.0, "blocked_by": []},
            {"task": "Wire session_id lookup into resume-all.py cross-host path", "priority": 3, "effort_h": 1.0, "blocked_by": []},
            {"task": "Add --host flag to resume-bridge (skip SSH config lookup)", "priority": 4, "effort_h": 0.5, "blocked_by": []},
            {"task": "Voice-activate: detect PyObjC availability, fall back gracefully", "priority": 5, "effort_h": 0.5, "blocked_by": []},
            {"task": "WezTerm backend in detect_backend()", "priority": 6, "effort_h": 4.0, "blocked_by": []},
            {"task": "Windows backend (named pipes, tasklist)", "priority": 7, "effort_h": 8.0, "blocked_by": []},
            {"task": "Cross-host resume open WezTerm from macOS", "priority": 8, "effort_h": 6.0, "blocked_by": []},
            {"task": "E08-E09 (sentiment, telemetry)", "priority": 9, "effort_h": 8.0, "blocked_by": []},
        ],
    }


def omniroute_audit_data():
    return {
        "name": "omniroute-audit",
        "summary": "Audit documents for OmniRoute (7 markdown files, ~37 KB). Tier-1 PR drafts + codebase audit findings.",
        "epics": [
            {"name": "Tier-1 PR drafts", "status": "done", "progress_pct": 100, "goals": [
                {"name": "04-tier1-pr-drafts.md (11.4 KB)", "status": "done"},
                {"name": "07-real-tier1-targets.md", "status": "done"},
            ]},
            {"name": "Codebase audit", "status": "done", "progress_pct": 100, "goals": [
                {"name": "06-real-codebase-audit.md", "status": "done"},
                {"name": "05-fix-electrobun-branch-audit.md", "status": "done"},
            ]},
            {"name": "Problem statement docs", "status": "done", "progress_pct": 100, "goals": [
                {"name": "01-where-the-question-lives.md", "status": "done"},
                {"name": "02-why-the-naive-reply-fails.md", "status": "done"},
                {"name": "03-corrected-reply.md", "status": "done"},
            ]},
        ],
        "backlog": [
            {"task": "Open Tier-1 PRs against OmniRoute upstream", "priority": 1, "effort_h": 4.0, "blocked_by": []},
        ],
    }


def omniroute_prs_data():
    return {
        "name": "omniroute-prs",
        "summary": "Worktree of OmniRoute upstream (87+ subdirs). Used for staging PRs.",
        "epics": [
            {"name": "Upstream worktree", "status": "done", "progress_pct": 100, "goals": [
                {"name": "omniroute upstream synced to 87 dirs", "status": "done"},
            ]},
            {"name": "Tier-1 branches ready for PR", "status": "pending", "progress_pct": 0, "goals": [
                {"name": "Create branches from audit findings", "status": "pending", "effort_h": 6},
            ]},
        ],
        "backlog": [
            {"task": "Push tier-1 branches to forks", "priority": 1, "effort_h": 2.0, "blocked_by": []},
        ],
    }


def phenotype_registry_data():
    return {
        "name": "Phenotype-registry",
        "summary": "Phenotype registry of absorbed crates (currently empty absorbed-crates subdir).",
        "epics": [
            {"name": "absorbed-crates registry", "status": "pending", "progress_pct": 0, "goals": [
                {"name": "Populate absorbed-crates with new entries", "status": "pending", "effort_h": 4},
            ]},
        ],
        "backlog": [
            {"task": "Define registry schema (TOML/JSON)", "priority": 1, "effort_h": 1.0, "blocked_by": []},
        ],
    }


def session_snapshot_data():
    return {
        "name": "session-snapshot",
        "summary": "Cross-harness session snapshot library (10 .py files + 5 tests). Used by /Users/kooshapari/bin/session_snapshot.py.",
        "epics": [
            {"name": "Collector + Orchestrator", "status": "done", "progress_pct": 100, "goals": [
                {"name": "collector.py + orchestrator.py + pane.py", "status": "done"},
                {"name": "__main__.py entry point", "status": "done"},
            ]},
            {"name": "Resolvers", "status": "done", "progress_pct": 100, "goals": [
                {"name": "resolvers/ subdir (Codex, Cursor, Kilo, OpenCode, Droid)", "status": "done"},
            ]},
            {"name": "Tests", "status": "in_progress", "progress_pct": 80, "goals": [
                {"name": "5 test files (test_collector, test_orchestrator, test_resolver_codex, test_resolver_cursor, conftest)", "status": "done"},
                {"name": "Coverage report + badge", "status": "pending", "effort_h": 2},
            ]},
        ],
        "backlog": [
            {"task": "Add CI for session-snapshot (pytest + coverage)", "priority": 1, "effort_h": 2.0, "blocked_by": []},
            {"task": "Sync upstream bin/session_snapshot.py changes back to repo", "priority": 2, "effort_h": 1.0, "blocked_by": []},
        ],
    }


# ---------- Main ----------
def main():
    timestamp, status = get_health_tick()
    assets = count_assets()
    sentiment = load_sentiment_buckets()
    telemetry = load_telemetry_latest()

    data = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cockpit_tick": {
            "timestamp": timestamp,
            "status": status,
            "version": "v0.5.0",
        },
        "summary": {
            "total_repos": 6,
            "test_count_total": 343,
            "launchd_jobs": assets["launchd_jobs"],
            "bin_scripts": assets["bin_scripts"],
            "rust_crates": assets["rust_crates"],
            "config_files": assets["configs"],
        },
        "sentiment": sentiment,
        "telemetry": telemetry,
        "cross_host": get_cross_host_snapshot(),
        "bridge_health": get_bridge_health_latest(),
        "tailscale_watch": get_tailscale_watch_latest(),
        "bridge_history": get_bridge_history_summary(),
        "repos": [
            resume_all_data(),
            phenotype_data(),
            omniroute_audit_data(),
            omniroute_prs_data(),
            phenotype_registry_data(),
            session_snapshot_data(),
        ],
        "assets": assets,
    }

    # Build HTML
    html = build_html(data)
    out_file, _, content_hash = write_dashboard_artifacts(data, html)

    print(f"cockpit-dashboard: wrote {out_file}")
    print(f"  hash: {content_hash}")
    print(f"  size: {len(html):,} bytes")
    print(f"  status: {status}")
    return 0


def write_dashboard_artifacts(data, html):
    """Create content-addressed dashboard artifacts without removing prior output."""
    structural = json.dumps(data, sort_keys=True, separators=(",", ":"))
    structural_for_hash = structural.replace(data["generated_at"], "<TIMESTAMP>")
    content_hash = hashlib.sha256(structural_for_hash.encode()).hexdigest()[:8]
    data_snapshot = DASHBOARD_DIR / f"cockpit-data-{content_hash}.json"
    out_file = DASHBOARD_DIR / f"cockpit-{content_hash}.html"

    if not data_snapshot.exists():
        data_snapshot.write_text(json.dumps(data, indent=2) + "\n")
    if not out_file.exists():
        out_file.write_text(html)

    return out_file, data_snapshot, content_hash


def build_html(data):
    """Build the dashboard HTML."""
    # Color helpers
    status_colors = {
        "HEALTHY": "#10b981",
        "OK": "#10b981",
        "DEGRADED": "#f59e0b",
        "FAIL": "#ef4444",
        "CRITICAL": "#ef4444",
        "UNKNOWN": "#6b7280",
    }
    status_icons = {
        "done": "✓",
        "in_progress": "◐",
        "pending": "○",
        "blocked": "✗",
    }

    tick = data["cockpit_tick"]
    status_color = status_colors.get(tick["status"], "#6b7280")
    sentiment = data.get("sentiment", {})
    telemetry = data.get("telemetry", {}) or {}

    # Build alert banner based on telemetry + cockpit status
    alerts = []
    if tick["status"] in ("DEGRADED", "FAIL", "CRITICAL"):
        alerts.append(("critical",
            f"Cockpit {tick['status']} — "
            f"check ~/Library/Logs/resume-all/ for details"))
    if telemetry and not telemetry.get("ipc_healthy"):
        alerts.append(("error",
            f"IPC daemon degraded (since {telemetry.get('ts','?')}) — "
            f"run resume-all ipc-recover"))
    if telemetry and telemetry.get("launchd_jobs_degraded", 0) > 0:
        n = telemetry["launchd_jobs_degraded"]
        alerts.append(("warning",
            f"{n} launchd job(s) degraded — check launchctl print"))
    if telemetry:
        snap_age = telemetry.get("snapshot_stale_seconds", 0)
        if snap_age > 90:
            alerts.append(("warning",
                f"Snapshot stale ({snap_age:.0f}s old) — "
                f"trigger resume-all snapshot"))

    # Cross-host snapshot alerts (only for hosts with data we care about)
    cross_host = data.get("cross_host", {}) or {}
    for host, info in cross_host.items():
        if info.get("stale") and info.get("rows", 0) > 0:
            alerts.append(("info",
                f"Cross-host {host}: snapshot is {info['age_seconds']}s old "
                f"({info['rows']} rows from {info.get('harness_count', '?')} harnesses)"))

    # Bridge health alerts
    bridge_health = data.get("bridge_health")
    if bridge_health and not bridge_health.get("healthy"):
        alerts.append(("error",
            f"Cross-host bridge DEGRADED "
            f"(exit={bridge_health.get('exit_code', '?')}, "
            f"since {bridge_health.get('ts', '?')})"))
        sid = telemetry.get("with_session_id", 0)
        total = telemetry.get("total_sessions", 1)
        if total and sid / total < 0.05:
            alerts.append(("info",
                f"Only {sid}/{total} sessions have session_id — "
                f"resolvers may need attention"))
    if sentiment.get("bad", 0) > 0:
        alerts.append(("warning",
            f"{sentiment['bad']} session(s) with bad sentiment — "
            f"review via sentiment-sessions.py --bucket=bad"))

    alerts_html = ""
    if alerts:
        alert_colors = {
            "critical": "#dc2626", "error": "#ef4444",
            "warning": "#f59e0b", "info": "#3b82f6",
        }
        alerts_html = '<div style="margin-bottom:1rem;">'
        for level, msg in alerts:
            color = alert_colors.get(level, "#6b7280")
            alerts_html += (
                f'<div style="background:{color}22;border-left:4px solid {color};'
                f'padding:0.6rem 1rem;margin-bottom:0.5rem;border-radius:4px;">'
                f'<strong style="color:{color};text-transform:uppercase;">'
                f'{level}</strong> &nbsp; {msg}</div>'
            )
        alerts_html += '</div>'
    # Inject into HTML
    return _build_html_template(data, alerts_html)


def _build_html_template(data, alerts_html):
    """Original template body. Renamed so build_html can compose alerts + template."""
    # Color helpers (kept for backward compat)
    status_colors = {
        "HEALTHY": "#10b981", "OK": "#10b981",
        "DEGRADED": "#f59e0b", "FAIL": "#ef4444",
        "CRITICAL": "#ef4444", "UNKNOWN": "#6b7280",
    }
    status_icons = {
        "done": "✓", "in_progress": "◐", "pending": "○", "blocked": "✗",
    }

    tick = data["cockpit_tick"]
    status_color = status_colors.get(tick["status"], "#6b7280")
    sentiment = data.get("sentiment", {})
    telemetry = data.get("telemetry", {}) or {}

    # Sentiment histogram HTML
    sentiment_html = ""
    if any(sentiment.values()):
        total_sent = sum(sentiment.values()) or 1
        bucket_colors = {
            "great": "#10b981", "good": "#34d399", "neutral": "#6b7280",
            "concerning": "#f59e0b", "bad": "#ef4444",
        }
        for b in ["great", "good", "neutral", "concerning", "bad"]:
            n = sentiment.get(b, 0)
            pct = n / total_sent * 100
            color = bucket_colors[b]
            sentiment_html += f'''
            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.25rem;">
              <span style="width:80px;color:{color};font-weight:bold;">{b}</span>
              <div style="flex:1;background:#1e293b;border-radius:4px;height:18px;overflow:hidden;">
                <div style="background:{color};width:{pct}%;height:100%;transition:width 0.5s;"></div>
              </div>
              <span style="width:80px;text-align:right;font-family:monospace;">{n} ({pct:.1f}%)</span>
            </div>'''

    # Telemetry summary HTML
    telemetry_html = ""
    cross_host = data.get("cross_host", {}) or {}
    if telemetry:
        ipc_status = "OK" if telemetry.get("ipc_healthy") else "DEGRADED"
        ipc_color = "#10b981" if telemetry.get("ipc_healthy") else "#ef4444"
        telemetry_html = f'''
    <div class="stat"><div class="stat-value" style="color:{ipc_color};">{ipc_status}</div><div class="stat-label">IPC ({telemetry.get("ipc_managed_processes", 0)})</div></div>
    <div class="stat"><div class="stat-value">{telemetry.get("with_session_id", 0)}/{telemetry.get("total_sessions", 0)}</div><div class="stat-label">SID/total</div></div>
    <div class="stat"><div class="stat-value">{telemetry.get("unique_harnesses", 0)}</div><div class="stat-label">Harnesses</div></div>'''
        # Cross-host stat (always rendered, even if telemetry empty, since cross_host is independent)
        if cross_host:
            total_rows = sum(h.get("rows", 0) for h in cross_host.values() if not h.get("error"))
            healthy_hosts = sum(1 for h in cross_host.values()
                                if not h.get("stale") and h.get("rows", 0) > 0)
            stale_hosts = len(cross_host) - healthy_hosts
            ch_color = "#10b981" if stale_hosts == 0 else "#f59e0b"
            ch_html = '<div class="stat" title="Cross-host Phase B bridge rows">'
            ch_html += f'<div class="stat-value" style="color:{ch_color};">{total_rows}</div>'
            ch_html += f'<div class="stat-label">Cross-host rows ({healthy_hosts}/{len(cross_host)} hosts)</div></div>'
            # Add per-host detail rows under the stats
            ch_html += '<div style="margin-top:0.5rem;display:flex;flex-wrap:wrap;gap:0.5rem;justify-content:center;">'
            for host, info in sorted(cross_host.items()):
                if info.get("error"):
                    continue
                rows = info.get("rows", 0)
                if rows == 0 and info.get("stale"):
                    badge_color = "#6b7280"
                    badge_text = "empty/stale"
                elif info.get("stale"):
                    badge_color = "#f59e0b"
                    badge_text = f"{rows}r/{info.get('age_seconds', '?')}s"
                else:
                    badge_color = "#10b981"
                    badge_text = f"{rows}r/{info.get('age_seconds', '?')}s"
                ch_html += (
                    f'<span style="background:{badge_color}22;border:1px solid {badge_color};'
                    f'padding:2px 8px;border-radius:10px;font-size:0.75em;font-family:monospace;">'
                    f'<span style="color:{badge_color};font-weight:bold;">{host}</span> '
                    f'<span style="opacity:0.8;">{badge_text}</span></span>'
                )
            ch_html += '</div>'
            telemetry_html += ch_html
        # Bridge health stat (independent of telemetry)
        bridge_health = data.get("bridge_health")
        if bridge_health:
            bh_status = "OK" if bridge_health.get("healthy") else "DEGRADED"
            bh_color = "#10b981" if bridge_health.get("healthy") else "#ef4444"
            telemetry_html += (
                f'<div class="stat" title="Cross-host bridge daemon health (60s tick)">'
                f'<div class="stat-value" style="color:{bh_color};">{bh_status}</div>'
                f'<div class="stat-label">Bridge ({bridge_health.get("exit_code", "?")})</div></div>'
            )
        # Tailscale watch stat
        ts = data.get("tailscale_watch")
        if ts:
            ts_state = ts.get("state", "?")
            ts_color = "#10b981" if ts_state == "up" else "#ef4444"
            ts_routes = "RT" if ts.get("has_tailscale_routes") == "true" else ""
            ts_daemon = "PG" if ts.get("daemon_pid_running") == "true" else ""
            ts_title = (f"Tailscale daemon state (60s tick). "
                        f"Routes={ts.get('has_tailscale_routes')}, "
                        f"pgrep={ts.get('daemon_pid_running')}, "
                        f"status_exit={ts.get('status_exit_code')}, "
                        f"hosts={ts.get('host_lines')}, last={ts.get('ts_iso', '?')}")
            telemetry_html += (
                f'<div class="stat" title="{ts_title}">'
                f'<div class="stat-value" style="color:{ts_color};">{ts_state.upper()}</div>'
                f'<div class="stat-label">Tailscale {ts_routes}{ts_daemon}</div></div>'
            )
        # Bridge history sparkline (24h trend)
        bh = data.get("bridge_history")
        if bh and bh.get("total_ticks", 0) > 0:
            states = bh.get("last_states", [])
            n = len(states)
            uptime = bh.get("uptime_pct", 0.0)
            rows_per_host = bh.get("latest_rows_per_host", {})
            host_summary = ", ".join(f"{h}={r}r" for h, r in rows_per_host.items())
            # Build inline SVG sparkline
            spark_w = 240
            spark_h = 36
            bar_w = max(2, spark_w // max(n, 1))
            bars = []
            for i, healthy in enumerate(states):
                x = i * bar_w
                color = "#10b981" if healthy else "#ef4444"
                bars.append(f'<rect x="{x}" y="0" width="{bar_w - 1}" height="{spark_h}" fill="{color}" opacity="0.85"/>')
            spark_svg = (
                f'<svg width="{spark_w}" height="{spark_h}" viewBox="0 0 {spark_w} {spark_h}" '
                f'xmlns="http://www.w3.org/2000/svg" style="background:#0f172a;border-radius:4px;">'
                + "".join(bars)
                + "</svg>"
            )
            uptime_color = "#10b981" if uptime >= 80 else ("#f59e0b" if uptime >= 50 else "#ef4444")
            bh_title = (f"Bridge health history (last {n} ticks, 5min interval). "
                        f"uptime={uptime:.1f}% ({bh.get('healthy_count', 0)}/{n} healthy). "
                        f"latest: {host_summary}")
            telemetry_html += (
                f'<div class="stat" style="min-width:280px;" title="{bh_title}">'
                f'<div class="stat-value" style="color:{uptime_color};">{uptime:.0f}%</div>'
                f'<div class="stat-label">Bridge uptime ({n} ticks)</div>'
                f'<div style="margin-top:0.4rem;">{spark_svg}</div>'
                f"</div>"
            )
        if telemetry.get("ts"):
            telemetry_html += f'<p style="text-align:center;opacity:0.5;font-size:0.8em;margin-top:0.5rem;">telemetry tick: {telemetry.get("ts", "?")}</p>'

    # Build per-repo HTML
    repo_html = ""
    overall_progress = 0
    overall_count = 0

    for repo in data["repos"]:
        # Compute repo progress: average of epic progress
        epic_progresses = []
        epic_html = ""
        for epic in repo["epics"]:
            pct = epic["progress_pct"]
            epic_progresses.append(pct)
            color = status_colors.get({
                "done": "HEALTHY",
                "in_progress": "DEGRADED",
                "pending": "UNKNOWN",
                "blocked": "CRITICAL",
            }.get(epic["status"], "UNKNOWN"), "#6b7280")
            goal_html = ""
            for goal in epic["goals"]:
                icon = status_icons.get(goal["status"], "○")
                g_color = status_colors.get({
                    "done": "HEALTHY",
                    "in_progress": "DEGRADED",
                    "pending": "UNKNOWN",
                    "blocked": "CRITICAL",
                }.get(goal["status"], "UNKNOWN"), "#6b7280")
                effort = ""
                if "effort_h" in goal:
                    effort = f' <span style="opacity:0.6;font-size:0.85em;">({goal["effort_h"]}h)</span>'
                goal_html += f'<li><span style="color:{g_color};font-weight:bold;">{icon}</span> {goal["name"]}{effort}</li>'

            epic_html += f'''
            <div style="margin-bottom:0.8rem;">
              <div style="display:flex;justify-content:space-between;margin-bottom:0.25rem;">
                <strong>{epic["name"]}</strong>
                <span style="opacity:0.7;">{epic["status"].upper()} — {pct}%</span>
              </div>
              <div style="background:#1f2937;border-radius:4px;height:14px;overflow:hidden;">
                <div style="background:{color};width:{pct}%;height:100%;transition:width 0.5s;"></div>
              </div>
              <ul style="margin-top:0.4rem;margin-bottom:0.5rem;font-size:0.9em;opacity:0.85;list-style:none;padding-left:0;">
                {goal_html}
              </ul>
            </div>'''

        repo_pct = int(sum(epic_progresses) / len(epic_progresses)) if epic_progresses else 0
        overall_progress += repo_pct
        overall_count += 1

        # Backlog table rows
        backlog_rows = ""
        for item in repo["backlog"]:
            blocked = ", ".join(item["blocked_by"]) if item["blocked_by"] else "—"
            blocked_color = "#ef4444" if item["blocked_by"] else "#9ca3af"
            backlog_rows += f'''
              <tr>
                <td style="text-align:center;font-weight:bold;color:#a78bfa;">#{item["priority"]}</td>
                <td>{item["task"]}</td>
                <td style="text-align:center;">{item["effort_h"]}h</td>
                <td style="color:{blocked_color};font-size:0.85em;">{blocked}</td>
              </tr>'''

        repo_html += f'''
        <details open style="margin-bottom:2rem;border:1px solid #374151;border-radius:8px;padding:1rem;">
          <summary style="cursor:pointer;font-size:1.3rem;font-weight:bold;display:flex;justify-content:space-between;align-items:center;">
            <span>{repo["name"]} <span style="opacity:0.6;font-size:0.7em;font-weight:normal;">— {repo["summary"]}</span></span>
            <span style="background:linear-gradient(90deg,#3b82f6,#8b5cf6);padding:0.25rem 0.75rem;border-radius:999px;font-size:0.8em;color:white;">{repo_pct}%</span>
          </summary>
          <div style="margin-top:1rem;">
            <h4 style="margin:0 0 0.5rem 0;color:#a78bfa;">Epic Progress (DAG)</h4>
            {epic_html}
            {f'''
            <h4 style="margin:1.5rem 0 0.5rem 0;color:#a78bfa;">Sub-repos (intra-repo)</h4>
            <table style="width:100%;border-collapse:collapse;font-size:0.9em;">
              <thead>
                <tr style="background:#1f2937;">
                  <th style="padding:0.4rem;">Name</th>
                  <th style="padding:0.4rem;">Branch</th>
                  <th style="padding:0.4rem;">Date</th>
                  <th style="padding:0.4rem;">Commits/30d</th>
                  <th style="padding:0.4rem;">TODOs</th>
                  <th style="padding:0.4rem;">Findings</th>
                  <th style="padding:0.4rem;">WT</th>
                  <th style="padding:0.4rem;">Last commit</th>
                </tr>
              </thead>
              <tbody>
                {repo["sub_repos_table"]}
              </tbody>
            </table>
            ''' if repo.get("sub_repos_table") else ''}
            <h4 style="margin:1.5rem 0 0.5rem 0;color:#a78bfa;">Backlog</h4>
            <table style="width:100%;border-collapse:collapse;font-size:0.9em;">
              <thead>
                <tr style="background:#1f2937;">
                  <th style="padding:0.5rem;">Pri</th>
                  <th style="padding:0.5rem;">Task</th>
                  <th style="padding:0.5rem;">Effort</th>
                  <th style="padding:0.5rem;">Blocked by</th>
                </tr>
              </thead>
              <tbody>
                {backlog_rows}
              </tbody>
            </table>
          </div>
        </details>'''

    overall_pct = int(overall_progress / overall_count) if overall_count else 0
    s = data["summary"]

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Cockpit Dashboard — resume-all multi-repo backlog</title>
  <style>
    body {{ font-family: ui-sans-serif, -apple-system, system-ui, sans-serif;
           max-width: 1100px; margin: 1.5rem auto; padding: 0 1.5rem;
           background: #0f172a; color: #f3f4f6; line-height: 1.5; }}
    h1 {{ border-bottom: 2px solid #374151; padding-bottom: 0.5rem; margin-bottom: 0.5rem; }}
    h2 {{ color: #93c5fd; margin-top: 1.5rem; }}
    h3 {{ color: #a78bfa; }}
    code {{ background: #1f2937; padding: 1px 6px; border-radius: 3px; font-family: ui-monospace, "SF Mono", Menlo, monospace; }}
    .cockpit-tick {{
      background: linear-gradient(135deg, #1e293b, #0f172a);
      border: 1px solid #374151;
      border-radius: 8px;
      padding: 1rem 1.25rem;
      margin-bottom: 1.5rem;
      display: grid;
      grid-template-columns: auto 1fr auto auto;
      gap: 1rem;
      align-items: center;
    }}
    .tick-pulse {{
      width: 12px; height: 12px; border-radius: 50%;
      background: {status_color};
      box-shadow: 0 0 12px {status_color};
      animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.6; transform: scale(1.2); }}
    }}
    .tick-status {{
      font-size: 1.4rem; font-weight: bold; color: {status_color};
    }}
    .tick-meta {{ font-size: 0.85em; opacity: 0.75; }}
    .overall-progress {{
      background: #1f2937;
      border-radius: 8px;
      padding: 1rem;
      margin-bottom: 1.5rem;
    }}
    .stat-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 0.75rem;
      margin-top: 1rem;
    }}
    .stat {{
      background: #1e293b;
      border: 1px solid #374151;
      border-radius: 6px;
      padding: 0.75rem;
      text-align: center;
    }}
    .stat-value {{ font-size: 1.6rem; font-weight: bold; color: #93c5fd; }}
    .stat-label {{ font-size: 0.8em; opacity: 0.7; text-transform: uppercase; letter-spacing: 0.05em; }}
    .footer {{ text-align: center; opacity: 0.5; font-size: 0.8em; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #374151; }}
    summary::marker {{ color: #93c5fd; }}
  </style>
  <script>
    // Auto-refresh every 30s to pick up new health-check + structural changes
    (function() {{
      const REFRESH_MS = 30000;
      let countdown = REFRESH_MS / 1000;
      function tick() {{
        const el = document.getElementById("refresh-countdown");
        if (el) el.textContent = `next refresh in ${{countdown}}s`;
        countdown--;
        if (countdown < 0) location.reload();
      }}
      setInterval(tick, 1000);
      tick();
    }})();
  </script>
</head>
<body>
  <h1>🛩️ Cockpit Dashboard</h1>
  <p style="opacity:0.7;">resume-all multi-repo backlog · {tick["version"]} · generated {data["generated_at"]}</p>

  <div class="cockpit-tick">
    <div class="tick-pulse"></div>
    <div>
      <div class="tick-status">{tick["status"]}</div>
      <div class="tick-meta">Last tick: {tick["timestamp"]}</div>
    </div>
    <div class="tick-meta">overall {overall_pct}%</div>
    <div class="tick-meta">{s["total_repos"]} repos · {s["test_count_total"]} tests</div>
    <div class="tick-meta" id="refresh-countdown" style="color:#10b981;">next refresh in 30s</div>
  </div>

  {{ALERTS}}

  <div class="overall-progress">
    <h3 style="margin-top:0;">Overall Progress (all repos)</h3>
    <div style="background:#0f172a;border-radius:6px;height:24px;overflow:hidden;border:1px solid #374151;">
      <div style="background:linear-gradient(90deg,#3b82f6,#8b5cf6,#ec4899);width:{overall_pct}%;height:100%;display:flex;align-items:center;justify-content:center;font-weight:bold;color:white;font-size:0.85em;">{overall_pct}%</div>
    </div>
    <div class="stat-grid">
      <div class="stat"><div class="stat-value">{s["launchd_jobs"]}</div><div class="stat-label">Launchd jobs</div></div>
      <div class="stat"><div class="stat-value">{s["bin_scripts"]}</div><div class="stat-label">Bin scripts</div></div>
      <div class="stat"><div class="stat-value">{s["rust_crates"]}</div><div class="stat-label">Rust crates</div></div>
      <div class="stat"><div class="stat-value">{s["test_count_total"]}</div><div class="stat-label">Tests</div></div>
      <div class="stat"><div class="stat-value">{s["config_files"]}</div><div class="stat-label">Config TOMLs</div></div>
      {telemetry_html}
    </div>
    {f'''
    <h3 style="margin-top:1.5rem;">Session Sentiment (E08)</h3>
    <p style="opacity:0.7;font-size:0.85em;margin-top:0;">Bucket distribution across {sum(sentiment.values())} sessions</p>
    {sentiment_html}
    ''' if any(sentiment.values()) else ''}
  </div>

  <h2>📊 Per-Repo DAG Tree Progress</h2>
  {repo_html}

  <div class="footer">
    <p>Hash-based filename: {Path(DATA_FILE).parent.glob("cockpit-*.html").__next__().name if list(DATA_FILE.parent.glob("cockpit-*.html")) else "n/a"}</p>
    <p>Sources: {HANDOFF.name}, /Users/kooshapari/bin/*.py, /Users/kooshapari/thegent/crates/, /Users/kooshapari/CodeProjects/*</p>
    <p>Generated by /Users/kooshapari/bin/cockpit-dashboard.py</p>
  </div>
</body>
</html>'''.replace("{ALERTS}", alerts_html)


from pathlib import Path
if __name__ == "__main__":
    sys.exit(main())
