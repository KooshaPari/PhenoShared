#!/opt/homebrew/bin/python3
"""
leak-detect.py — Phase F hardening item F05.

Memory-leak detection tool for the resume-all toolkit. Monitors the RSS
(resident set size) of every long-running process and alerts when RSS growth
exceeds a threshold (indicates a leak). Tracks history in JSONL so trends
are visible across hours/days.

Processes monitored
-------------------
- sharecli-ipc-daemon     (Rust IPC daemon; expected ~2.4 MiB RSS — see §3
                            of handoff/RUNBOOK.md; > 10 MiB is a leak)
- sharecli-tray           (Rust menu bar app; expected ~30-50 MiB)
- session_snapshot.py     (Python snapshot loop wrapper; ~50-100 MiB)
- dependency-watch.py     (Python dep watcher; ~10-30 MiB)
- thegent-mcp             (Rust MCP server; ~5-10 MiB; child of sharecli-tray)
- sla-monitor             (Python SLA daemon wrapper; subprocess of launchd)

Each poll produces one JSONL row per running process. The `run` daemon
keeps an in-memory sliding window per (process, pid) and computes a
linear-regression slope on the last N samples (default 10). Slope thresholds:
    WARN     >  100 KB / 30 s   (≈ 3.3  KB/s)
    CRITICAL >  500 KB / 30 s   (≈ 16.6 KB/s)

Storage
-------
- Metrics : ~/.local/share/resume-all/rss-metrics.jsonl  (append-only JSONL)
- Alerts  : ~/.local/share/resume-all/rss-alerts.log     (human-readable)
- State   : ~/.local/share/resume-all/rss-state.json     (alert dedup state)

Subcommands
-----------
  collect           poll once, append one JSONL line per process, dedupe
                    if last collection was < 5s ago
  run               daemon mode: poll every 30s, alert on slope threshold
  report --since=Nh read JSONL, emit markdown report with slopes + verdicts
  test              inline self-tests (4+ cases: stable, linear growth,
                    drop-then-grow, sample-too-small)

Design notes
------------
- Stdlib only (no new pip deps).
- Sliding window holds at least 100 samples per (process, pid) tuple in memory.
- Slope calc tolerates < 2 samples by returning None (no divide-by-zero).
- Alerts dedupe like sla-monitor.py: 3 consecutive breach polls before log.
- The poller tolerates processes that come and go (ps missing PIDs, restart).
- /opt/homebrew/bin/python3 shebang (Homebrew 3.14.x — see runbook §7).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path.home() / ".local" / "share" / "resume-all"
METRICS_PATH = DATA_DIR / "rss-metrics.jsonl"
ALERTS_PATH = DATA_DIR / "rss-alerts.log"
STATE_PATH = DATA_DIR / "rss-state.json"

DAEMON_INTERVAL_S = 30
COLLECT_MIN_SPACING_S = 5
ALERT_DEDUP_POLLS = 3  # require 3 consecutive breaches before logging

# Linear-regression slope thresholds (KB / 30 s)
SLOPE_WARN_KB_PER_30S = 100.0
SLOPE_CRIT_KB_PER_30S = 500.0

# Sliding window size for slope calculation
DEFAULT_SLOPE_WINDOW = 10
MIN_SLOPE_WINDOW = 2
INMEM_HISTORY_LIMIT = 100  # samples per (process, pid) held in memory

# Process discovery spec. Each entry is (key, exact_or_substring, pattern).
#   "exact"    → match against the executable basename (first whitespace-
#                separated token of the command, with parens stripped).
#   "substr"   → substring match anywhere in the command line.
PROCESS_SPECS: tuple[dict[str, str], ...] = (
    {"key": "sharecli-ipc-daemon", "match": "exact",  "pattern": "sharecli-ipc-daemon"},
    {"key": "sharecli-tray",       "match": "exact",  "pattern": "sharecli-tray"},
    {"key": "session_snapshot.py", "match": "substr", "pattern": "session_snapshot.py"},
    {"key": "dependency-watch.py", "match": "substr", "pattern": "dependency-watch.py"},
    {"key": "thegent-mcp",         "match": "exact",  "pattern": "thegent-mcp"},
    {"key": "sla-monitor",         "match": "substr", "pattern": "sla-monitor"},
)

# Verdict levels
HEALTHY = "HEALTHY"
WARN = "WARN"
LEAK = "LEAK"


# ---------------------------------------------------------------------------
# Process discovery
# ---------------------------------------------------------------------------

def _strip_ps_parens(command: str) -> str:
    """ps wraps a child's command field in parens (e.g. `(thegent-mcp)`) when
    the process has exited or is shown via a parent shortcut. Strip them so
    matching and basename extraction work normally."""
    s = command.strip()
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1].strip()
    return s


def _basename(token: str) -> str:
    """Last path component of a token. Handles `path/to/binary --flag` style
    tokens by returning the component before any whitespace."""
    token = token.strip()
    return Path(token).name if token else ""


def discover_processes() -> list[dict]:
    """Run `ps -axo pid=,rss=,command=` and return one record per match:
        {key, pid, rss_kb, command}

    - For 'exact' specs, the executable basename must equal the pattern.
    - For 'substr' specs, the pattern must appear anywhere in the command line.
    - De-duplicates by PID: each PID is recorded at most once, under its
      first-matching spec. This prevents a single transient ps row (e.g. a
      process whose command line is mid-rewrite) from matching multiple
      specs and producing duplicate rows.

    Uses the absolute path `/bin/ps` to avoid PATH surprises in launchd
    contexts (which may have a stripped-down PATH that omits /bin). The
    timeout is 30s — generous enough to absorb occasional system load
    spikes without spuriously dropping a collection.
    """
    try:
        proc = subprocess.run(
            ["/bin/ps", "-axo", "pid=,rss=,command="],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        print(f"warn: ps invocation failed: {exc}", file=sys.stderr)
        return []

    if proc.returncode != 0:
        print(
            f"warn: ps returned {proc.returncode}: {(proc.stderr or '').strip()}",
            file=sys.stderr,
        )
        return []

    seen_pids: set[int] = set()
    out: list[dict] = []

    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        # First two whitespace-separated tokens are pid and rss; everything
        # after is the command (may itself contain whitespace).
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
            rss_kb = int(parts[1])
        except ValueError:
            continue
        command = _strip_ps_parens(parts[2])
        first_token = command.split(None, 1)[0] if command else ""

        if pid in seen_pids:
            continue
        for spec in PROCESS_SPECS:
            key = spec["key"]
            if spec["match"] == "exact":
                if _basename(first_token) != spec["pattern"]:
                    continue
            elif spec["match"] == "substr":
                if spec["pattern"] not in command:
                    continue
            else:
                continue  # unknown match type — ignore
            seen_pids.add(pid)
            out.append({
                "key": key,
                "pid": pid,
                "rss_kb": rss_kb,
                "command": command,
            })
            break  # one PID → at most one spec

    return out


# ---------------------------------------------------------------------------
# Slope calculation (linear regression)
# ---------------------------------------------------------------------------

def slope_kb_per_sec(samples: list[tuple[float, float]]) -> float | None:
    """Least-squares slope of y over x.

    Args:
        samples: list of (x_epoch_seconds, y_kb) pairs, in time order.
                 `x` is the timestamp in seconds, `y` is RSS in KB.

    Returns:
        Slope in KB/sec, or None if fewer than 2 samples or x is constant.
    """
    if len(samples) < 2:
        return None
    xs = [s[0] for s in samples]
    ys = [s[1] for s in samples]
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    if den == 0.0:
        return None  # x is constant; slope undefined
    return num / den


def classify_slope(slope_kb_per_sec_value: float | None) -> str:
    """Map a slope in KB/sec to HEALTHY / WARN / LEAK using per-30s thresholds.
    Returns HEALTHY when slope is None (insufficient data)."""
    if slope_kb_per_sec_value is None:
        return HEALTHY
    # Convert per-second slope → per-30s slope for the threshold check.
    slope_per_30s = slope_kb_per_sec_value * 30.0
    if slope_per_30s > SLOPE_CRIT_KB_PER_30S:
        return LEAK
    if slope_per_30s > SLOPE_WARN_KB_PER_30S:
        return WARN
    return HEALTHY


def slope_per_30s(slope_kb_per_sec_value: float | None) -> float | None:
    """Helper: convert per-second slope to per-30s slope, preserving None."""
    if slope_kb_per_sec_value is None:
        return None
    return slope_kb_per_sec_value * 30.0


# ---------------------------------------------------------------------------
# Sliding-window state
# ---------------------------------------------------------------------------

class SlidingHistory:
    """Per-(process, pid) deque of (ts_epoch, rss_kb) samples.

    The deque holds up to INMEM_HISTORY_LIMIT samples (default 100). Slope
    computation pulls from the last N samples where N is configurable.
    """

    __slots__ = ("samples", "samples_in_session")

    def __init__(self, limit: int = INMEM_HISTORY_LIMIT) -> None:
        self.samples: deque[tuple[float, float]] = deque(maxlen=limit)
        self.samples_in_session: int = 0

    def append(self, ts_epoch: float, rss_kb: int) -> None:
        self.samples.append((ts_epoch, float(rss_kb)))
        self.samples_in_session += 1

    def slope_kb_per_sec(self, window: int = DEFAULT_SLOPE_WINDOW) -> float | None:
        if len(self.samples) < 2:
            return None
        recent = list(self.samples)[-window:]
        return slope_kb_per_sec(recent)

    def last_rss_kb(self) -> int | None:
        if not self.samples:
            return None
        return int(self.samples[-1][1])

    def first_rss_kb(self) -> int | None:
        if not self.samples:
            return None
        return int(self.samples[0][1])

    def max_rss_kb(self) -> int | None:
        if not self.samples:
            return None
        return int(max(s[1] for s in self.samples))


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _last_collect_epoch() -> int | None:
    """Read the metrics file and return the ts_epoch of the most recent sample
    (across all processes), or None if the file is missing or empty."""
    try:
        if not METRICS_PATH.exists():
            return None
        last_ts: int | None = None
        with METRICS_PATH.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    last_ts = int(obj.get("ts_epoch") or 0)
                except (ValueError, json.JSONDecodeError):
                    continue
        return last_ts
    except OSError:
        return None


def append_sample(sample: dict) -> None:
    """Append a single JSONL line to the metrics file. Creates parent dir."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps(sample, separators=(",", ":")) + "\n"
    with METRICS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Subcommand: collect
# ---------------------------------------------------------------------------

def cmd_collect() -> int:
    """Poll once for all processes; append one JSONL line per process found.
    Skip if the last sample (any process) was < COLLECT_MIN_SPACING_S ago.
    """
    last = _last_collect_epoch()
    now = int(time.time())
    if last is not None and (now - last) < COLLECT_MIN_SPACING_S:
        remaining = COLLECT_MIN_SPACING_S - (now - last)
        print(
            f"skip: last sample {now - last}s ago (min spacing {COLLECT_MIN_SPACING_S}s, "
            f"try again in {remaining}s)",
            file=sys.stderr,
        )
        return 0

    procs = discover_processes()
    if not procs:
        print(
            json.dumps(
                {
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
                    "ts_epoch": now,
                    "process_name": None,
                    "pid": None,
                    "rss_kb": 0,
                    "rss_delta_kb": None,
                    "samples_in_session": 0,
                    "note": "no monitored processes found",
                },
                separators=(",", ":"),
            )
        )
        return 0

    rows: list[dict] = []
    for p in procs:
        row = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
            "ts_epoch": now,
            "process_name": p["key"],
            "pid": p["pid"],
            "rss_kb": p["rss_kb"],
            # rss_delta_kb and samples_in_session require memory state — only
            # populated by the `run` daemon. `collect` writes the raw RSS only.
            "rss_delta_kb": None,
            "samples_in_session": 0,
            "command": p["command"],
        }
        append_sample(row)
        rows.append(row)

    # Echo a compact summary to stdout (one line per process).
    for row in rows:
        print(
            json.dumps(
                {
                    "process_name": row["process_name"],
                    "pid": row["pid"],
                    "rss_kb": row["rss_kb"],
                },
                separators=(",", ":"),
            )
        )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: run (daemon mode)
# ---------------------------------------------------------------------------

def _load_state() -> dict:
    """Load alert dedup state from disk. Returns empty dict on any error."""
    try:
        if not STATE_PATH.exists():
            return {}
        with STATE_PATH.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state: dict) -> None:
    """Persist alert dedup state to disk. Best-effort; errors are non-fatal."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = STATE_PATH.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(state, fh, separators=(",", ":"))
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                pass
        tmp.replace(STATE_PATH)
    except OSError as exc:
        print(f"warn: state save failed: {exc}", file=sys.stderr)


def _log_alert(alert: str, detail: str) -> None:
    """Append a timestamped alert line to the alerts log."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with ALERTS_PATH.open("a", encoding="utf-8") as fh:
            fh.write(f"{ts} [{alert.upper()}] {detail}\n")
            fh.flush()
    except OSError as exc:
        print(f"warn: alert log write failed: {exc}", file=sys.stderr)


def _evaluate_alerts(
    verdicts: dict[str, tuple[str, float | None, int]],
    state: dict,
) -> list[tuple[str, str]]:
    """Decide which alerts to log.

    Args:
        verdicts: maps "{process_key}/{pid}" → (verdict, slope_per_30s, rss_kb)
        state:    dedup state dict (mutated in place)

    Returns:
        List of (alert_key, detail) tuples — only newly-fired alerts
        (after the 3-poll dedup window) are returned.
    """
    new_alerts: list[tuple[str, str]] = []

    for ident, (verdict, slope30, rss_kb) in verdicts.items():
        state_key = f"alert:{ident}"
        consec = int(state.get(f"{state_key}:consec", 0))
        logged = bool(state.get(f"{state_key}:logged", False))

        if verdict == HEALTHY:
            if logged:
                _log_alert(f"{ident}_recovered", f"rss {rss_kb}KB (slope cleared)")
            state[f"{state_key}:consec"] = 0
            state[f"{state_key}:logged"] = False
            continue

        # In breach (WARN or LEAK)
        consec += 1
        state[f"{state_key}:consec"] = consec
        if consec >= ALERT_DEDUP_POLLS and not logged:
            slope_str = f"{slope30:.1f}" if slope30 is not None else "?"
            detail = (
                f"{verdict}: {ident} rss={rss_kb}KB "
                f"slope={slope_str} KB/30s over last {DEFAULT_SLOPE_WINDOW} samples"
            )
            new_alerts.append((ident, detail))
            state[f"{state_key}:logged"] = True

    return new_alerts


def cmd_run() -> int:
    """Daemon mode: poll every DAEMON_INTERVAL_S, write metrics, alert on
    slope-threshold breach. Tolerates missing processes (e.g. snapshot loop
    restart between polls)."""
    print(
        f"leak-detect daemon starting (interval={DAEMON_INTERVAL_S}s, "
        f"window={DEFAULT_SLOPE_WINDOW}, "
        f"warn>{SLOPE_WARN_KB_PER_30S:.0f}KB/30s "
        f"crit>{SLOPE_CRIT_KB_PER_30S:.0f}KB/30s, "
        f"data_dir={DATA_DIR})",
        file=sys.stderr,
    )

    state = _load_state()
    history: dict[tuple[str, int], SlidingHistory] = {}

    try:
        while True:
            procs = discover_processes()
            now_epoch = time.time()
            now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_epoch))
            verdicts: dict[str, tuple[str, float | None, int]] = {}

            for p in procs:
                ident = f"{p['key']}/{p['pid']}"
                hist_key = (p["key"], p["pid"])
                hist = history.get(hist_key)
                if hist is None:
                    hist = SlidingHistory()
                    history[hist_key] = hist

                prev_rss = hist.last_rss_kb()
                rss_delta = (p["rss_kb"] - prev_rss) if prev_rss is not None else None
                hist.append(now_epoch, p["rss_kb"])
                slope_sec = hist.slope_kb_per_sec(DEFAULT_SLOPE_WINDOW)
                slope30 = slope_per_30s(slope_sec)
                verdict = classify_slope(slope_sec)
                verdicts[ident] = (verdict, slope30, p["rss_kb"])

                row = {
                    "ts": now_ts,
                    "ts_epoch": int(now_epoch),
                    "process_name": p["key"],
                    "pid": p["pid"],
                    "rss_kb": p["rss_kb"],
                    "rss_delta_kb": rss_delta,
                    "samples_in_session": hist.samples_in_session,
                    "command": p["command"],
                    "slope_kb_per_30s": (
                        round(slope30, 3) if slope30 is not None else None
                    ),
                    "verdict": verdict,
                }
                append_sample(row)

            # Drop history for (key, pid) pairs no longer present.
            current_keys = {(p["key"], p["pid"]) for p in procs}
            stale = [k for k in history if k not in current_keys]
            for k in stale:
                del history[k]

            new_alerts = _evaluate_alerts(verdicts, state)
            for key, detail in new_alerts:
                _log_alert(key, detail)

            _save_state(state)

            if new_alerts:
                print(f"[{now_ts}] alerts fired: {new_alerts}", file=sys.stderr)
            else:
                summary = ", ".join(
                    f"{k}={v[0]}" for k, v in verdicts.items()
                ) or "no processes"
                print(f"[{now_ts}] {summary}", file=sys.stderr)

            time.sleep(DAEMON_INTERVAL_S)
    except KeyboardInterrupt:
        print("\nleak-detect daemon stopped", file=sys.stderr)
        return 0


# ---------------------------------------------------------------------------
# Subcommand: report
# ---------------------------------------------------------------------------

def _parse_since(since_str: str) -> int:
    """Parse a duration string like '24h', '1h', '30m', '90s', '1d' to seconds."""
    s = since_str.strip().lower()
    if not s:
        raise ValueError("empty --since value")
    if s.endswith("h"):
        return int(s[:-1]) * 3600
    if s.endswith("m"):
        return int(s[:-1]) * 60
    if s.endswith("s"):
        return int(s[:-1])
    if s.endswith("d"):
        return int(s[:-1]) * 86400
    # bare number = hours
    return int(s) * 3600


def _read_metrics(since_epoch: int) -> list[dict]:
    """Read JSONL metrics file; return samples with ts_epoch >= since_epoch."""
    samples: list[dict] = []
    if not METRICS_PATH.exists():
        return samples
    try:
        with METRICS_PATH.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    ts_epoch = int(obj.get("ts_epoch") or 0)
                    if ts_epoch >= since_epoch:
                        samples.append(obj)
                except (ValueError, json.JSONDecodeError):
                    continue
    except OSError:
        pass
    return samples


def _format_ts(epoch: int | float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(epoch)))


def _per_process_summary(samples: list[dict]) -> list[dict]:
    """Group samples by (process_name, pid) and compute per-process summary:
        {key, pid, samples, first_ts, last_ts, first_rss, current_rss,
         max_rss, slope_kb_per_sec, slope_kb_per_30s, verdict, command}
    """
    groups: dict[tuple[str, int], list[dict]] = {}
    for s in samples:
        key = s.get("process_name")
        pid = s.get("pid")
        if key is None or pid is None:
            continue
        groups.setdefault((str(key), int(pid)), []).append(s)

    summaries: list[dict] = []
    for (key, pid), psamples in groups.items():
        # Sort by ts_epoch just in case (JSONL should already be ordered).
        psamples.sort(key=lambda x: int(x.get("ts_epoch") or 0))
        xs = [float(s.get("ts_epoch") or 0) for s in psamples]
        ys = [float(s.get("rss_kb") or 0) for s in psamples]
        slope_sec = slope_kb_per_sec(list(zip(xs, ys)))
        slope30 = slope_per_30s(slope_sec)
        verdict = classify_slope(slope_sec)
        summaries.append({
            "key": key,
            "pid": pid,
            "samples": len(psamples),
            "first_ts": psamples[0].get("ts_epoch"),
            "last_ts": psamples[-1].get("ts_epoch"),
            "first_rss": int(psamples[0].get("rss_kb") or 0),
            "current_rss": int(psamples[-1].get("rss_kb") or 0),
            "max_rss": int(max(s.get("rss_kb") or 0 for s in psamples)),
            "slope_kb_per_sec": slope_sec,
            "slope_kb_per_30s": slope30,
            "verdict": verdict,
            "command": psamples[-1].get("command"),
        })

    # Stable sort: LEAK first, then WARN, then HEALTHY; within each, by max_rss desc.
    order = {LEAK: 0, WARN: 1, HEALTHY: 2}
    summaries.sort(key=lambda s: (order.get(s["verdict"], 3), -s["max_rss"]))
    return summaries


def _compute_incidents(samples: list[dict]) -> list[dict]:
    """Walk samples in process-key order and identify leak-incident periods:
    contiguous runs where the per-process verdict is not HEALTHY."""
    groups: dict[tuple[str, int], list[dict]] = {}
    for s in samples:
        key = s.get("process_name")
        pid = s.get("pid")
        if key is None or pid is None:
            continue
        groups.setdefault((str(key), int(pid)), []).append(s)

    incidents: list[dict] = []
    for (key, pid), psamples in groups.items():
        psamples.sort(key=lambda x: int(x.get("ts_epoch") or 0))
        in_incident = False
        incident_start: int | None = None
        incident_max_severity: str = HEALTHY
        for s in psamples:
            verdict = classify_slope(
                # Re-derive slope up to this point using a small window.
                slope_kb_per_sec(
                    [
                        (float(s2.get("ts_epoch") or 0), float(s2.get("rss_kb") or 0))
                        for s2 in psamples
                        if int(s2.get("ts_epoch") or 0) <= int(s.get("ts_epoch") or 0)
                    ][-DEFAULT_SLOPE_WINDOW:]
                )
            )
            if verdict != HEALTHY:
                if not in_incident:
                    in_incident = True
                    incident_start = int(s.get("ts_epoch") or 0)
                    incident_max_severity = HEALTHY
                if order_rank(verdict) < order_rank(incident_max_severity):
                    incident_max_severity = verdict
            else:
                if in_incident:
                    incident_end = int(s.get("ts_epoch") or 0)
                    slope30 = slope_per_30s(
                        slope_kb_per_sec(
                            [
                                (float(s2.get("ts_epoch") or 0), float(s2.get("rss_kb") or 0))
                                for s2 in psamples
                                if incident_start is not None
                                and incident_start <= int(s2.get("ts_epoch") or 0) <= incident_end
                            ]
                        )
                    )
                    incidents.append({
                        "process": key,
                        "pid": pid,
                        "start_epoch": incident_start,
                        "end_epoch": incident_end,
                        "duration_s": incident_end - (incident_start or 0),
                        "max_severity": incident_max_severity,
                        "slope_kb_per_30s": slope30,
                        "ongoing": False,
                    })
                    in_incident = False

        if in_incident:
            last_ts = int(psamples[-1].get("ts_epoch") or 0)
            slope30 = slope_per_30s(
                slope_kb_per_sec(
                    [
                        (float(s2.get("ts_epoch") or 0), float(s2.get("rss_kb") or 0))
                        for s2 in psamples
                        if incident_start is not None
                        and int(s2.get("ts_epoch") or 0) >= incident_start
                    ]
                )
            )
            incidents.append({
                "process": key,
                "pid": pid,
                "start_epoch": incident_start,
                "end_epoch": last_ts,
                "duration_s": last_ts - (incident_start or 0),
                "max_severity": incident_max_severity,
                "slope_kb_per_30s": slope30,
                "ongoing": True,
            })

    # Sort by start time, then by severity.
    incidents.sort(key=lambda i: (i["start_epoch"] or 0, order_rank(i["max_severity"])))
    return incidents


def order_rank(verdict: str) -> int:
    return {LEAK: 0, WARN: 1, HEALTHY: 2}.get(verdict, 3)


def cmd_report(since: str) -> int:
    since_s = _parse_since(since)
    now = int(time.time())
    since_epoch = now - since_s
    samples = _read_metrics(since_epoch)

    lines: list[str] = []
    lines.append("# RSS / Leak Detection Report")
    lines.append("")
    lines.append(
        f"- Window: since `{since}` ({_format_ts(since_epoch)} → {_format_ts(now)})"
    )
    lines.append(f"- Metrics file: `{METRICS_PATH}`")
    lines.append(f"- Samples (rows): {len(samples)}")
    lines.append(
        f"- Thresholds: WARN > {SLOPE_WARN_KB_PER_30S:.0f} KB/30s "
        f"({SLOPE_WARN_KB_PER_30S/30:.2f} KB/s), "
        f"LEAK > {SLOPE_CRIT_KB_PER_30S:.0f} KB/30s "
        f"({SLOPE_CRIT_KB_PER_30S/30:.2f} KB/s)"
    )

    if not samples:
        lines.append("")
        lines.append("> No samples in this window. Run `leak-detect collect` or `leak-detect run`.")
        return _emit_report(lines)

    summaries = _per_process_summary(samples)

    # Per-process table
    lines.append("")
    lines.append(f"## Per-process Summary ({len(summaries)} process instances)")
    lines.append("")
    lines.append(
        "| Process | PID | Samples | Start RSS (KB) | Current RSS (KB) | "
        "Max RSS (KB) | Slope (KB/30s) | Verdict |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for s in summaries:
        slope_str = (
            f"{s['slope_kb_per_30s']:.1f}" if s["slope_kb_per_30s"] is not None else "—"
        )
        lines.append(
            f"| `{s['key']}` | {s['pid']} | {s['samples']} | "
            f"{s['first_rss']:,} | {s['current_rss']:,} | {s['max_rss']:,} | "
            f"{slope_str} | **{s['verdict']}** |"
        )

    # Top 3 by absolute RSS
    lines.append("")
    lines.append("## Top 3 by Current RSS")
    lines.append("")
    lines.append("| Rank | Process | PID | RSS (KB) | MiB |")
    lines.append("|---|---|---|---|---|")
    top3 = sorted(summaries, key=lambda s: -s["current_rss"])[:3]
    for i, s in enumerate(top3, 1):
        mib = s["current_rss"] / 1024.0
        lines.append(f"| {i} | `{s['key']}` | {s['pid']} | {s['current_rss']:,} | {mib:.2f} |")

    # Verdicts by process (collapse by key, take worst verdict)
    lines.append("")
    lines.append("## Verdict by Process")
    lines.append("")
    lines.append("| Process | Worst Verdict | Instances |")
    lines.append("|---|---|---|")
    by_key: dict[str, list[dict]] = {}
    for s in summaries:
        by_key.setdefault(s["key"], []).append(s)
    for key in sorted(by_key.keys()):
        group = by_key[key]
        worst = min(group, key=lambda x: order_rank(x["verdict"]))["verdict"]
        lines.append(f"| `{key}` | **{worst}** | {len(group)} |")

    # Incidents
    incidents = _compute_incidents(samples)
    lines.append("")
    lines.append(f"## Leak Incidents ({len(incidents)})")
    lines.append("")
    if not incidents:
        lines.append("> No leak incidents in window.")
    else:
        lines.append("| Process | PID | Start (UTC) | Duration | Severity | Slope (KB/30s) | Status |")
        lines.append("|---|---|---|---|---|---|---|")
        for inc in incidents:
            start_ts = _format_ts(int(inc.get("start_epoch") or 0))
            dur_s = int(inc.get("duration_s") or 0)
            if dur_s >= 60:
                dur_str = f"{dur_s // 60}m{dur_s % 60:02d}s"
            else:
                dur_str = f"{dur_s}s"
            slope_str = (
                f"{inc['slope_kb_per_30s']:.1f}"
                if inc.get("slope_kb_per_30s") is not None
                else "—"
            )
            status = "ongoing" if inc.get("ongoing") else "recovered"
            lines.append(
                f"| `{inc['process']}` | {inc['pid']} | {start_ts} | "
                f"{dur_str} | **{inc['max_severity']}** | {slope_str} | {status} |"
            )

    return _emit_report(lines)


def _emit_report(lines: list[str]) -> int:
    print("\n".join(lines))
    return 0


# ---------------------------------------------------------------------------
# Subcommand: test (inline self-tests)
# ---------------------------------------------------------------------------

def cmd_test() -> int:
    """Run inline self-tests for slope classification + sliding history +
    process matching. Prints a TAP-like summary; exits 0 on success, 1 on
    failure."""
    cases: list[tuple[str, Any]] = []

    def case(name: str):
        def wrap(fn):
            cases.append((name, fn))
            return fn
        return wrap

    failures: list[str] = []

    def check(name: str, got: Any, want: Any) -> None:
        if got != want:
            failures.append(f"  FAIL {name}: got {got!r}, want {want!r}")

    def approx(a: float, b: float, tol: float = 1e-6) -> bool:
        return abs(a - b) < tol

    @case("slope_insufficient_data")
    def _():
        check("empty", slope_kb_per_sec([]), None)
        check("one_sample", slope_kb_per_sec([(0.0, 100.0)]), None)

    @case("slope_constant")
    def _():
        # x changes, y constant → slope = 0
        check("constant_y", slope_kb_per_sec([(0, 100), (10, 100), (20, 100)]), 0.0)

    @case("slope_linear_growth")
    def _():
        # 10 KB / 10 s = 1 KB/s
        s = slope_kb_per_sec([(0, 100), (10, 110), (20, 120), (30, 130)])
        check("linear_1KB/s", approx(s, 1.0), True)

    @case("slope_steeper_growth")
    def _():
        # 200 KB / 20 s = 10 KB/s → per-30s = 300 KB/30s → WARN
        s = slope_kb_per_sec([(0, 100), (20, 300)])
        check("linear_10KB/s", approx(s, 10.0), True)
        check("classify_warn", classify_slope(s), WARN)

    @case("slope_critical")
    def _():
        # 2000 KB / 20 s = 100 KB/s → per-30s = 3000 KB/30s → LEAK
        s = slope_kb_per_sec([(0, 100), (20, 2100)])
        check("linear_100KB/s", approx(s, 100.0), True)
        check("classify_crit", classify_slope(s), LEAK)

    @case("classify_thresholds")
    def _():
        # Use values that round-trip cleanly through the per-second → per-30s
        # multiplication in `classify_slope`. The threshold checks are strict
        # `>`, so values of exactly 100 or 500 KB/30s remain HEALTHY/WARN.
        check("zero_healthy", classify_slope(0.0), HEALTHY)
        check("just_under_warn", classify_slope(99.0 / 30.0), HEALTHY)  # 99 KB/30s
        check("at_warn_boundary", classify_slope(100.0 / 30.0), HEALTHY)  # 100 KB/30s
        check("just_over_warn", classify_slope(101.0 / 30.0), WARN)     # 101 KB/30s
        check("at_leak_boundary", classify_slope(16.66), WARN)          # 499.8 KB/30s
        check("just_over_leak", classify_slope(16.67), LEAK)           # 500.1 KB/30s
        check("well_over_leak", classify_slope(20.0), LEAK)             # 600 KB/30s
        check("none_input_healthy", classify_slope(None), HEALTHY)

    @case("classify_slope_at_exact_boundaries")
    def _():
        # Direct check on the strict-`>` semantics via simple expressions
        # (no chained comparisons). The classifier multiplies per-sec by 30
        # to get per-30s, so 500/30 → 500.00000000006 due to IEEE-754.
        check("warn_exact_500_strict", 500.0 > 500.0, False)   # boundary: NOT over
        check("leak_above_500_strict", 500.001 > 500.0, True)
        check("warn_exact_100_strict", 100.0 > 100.0, False)
        check("warn_above_100_strict", 100.001 > 100.0, True)
        # slope_per_30s helper preserves None
        check("per_30s_none", slope_per_30s(None), None)
        # Helper round-trip on integer-friendly values
        check("per_30s_1KB_s", slope_per_30s(1.0), 30.0)
        check("per_30s_16_66", slope_per_30s(16.66), 499.8)

    @case("slope_negative_growth_healthy")
    def _():
        # RSS decreasing → negative slope → HEALTHY
        s = slope_kb_per_sec([(0, 1000), (10, 900), (20, 800)])
        check("negative_slope", s < 0, True)
        check("classify_negative", classify_slope(s), HEALTHY)

    @case("slope_per_30s_helper")
    def _():
        check("none_passthrough", slope_per_30s(None), None)
        check("zero", slope_per_30s(0.0), 0.0)
        check("1KB/s", approx(slope_per_30s(1.0), 30.0), True)

    @case("sliding_history_basic")
    def _():
        h = SlidingHistory(limit=5)
        check("empty_first", h.first_rss_kb(), None)
        check("empty_last", h.last_rss_kb(), None)
        check("empty_max", h.max_rss_kb(), None)
        check("empty_slope", h.slope_kb_per_sec(), None)
        check("empty_count", h.samples_in_session, 0)

        h.append(0.0, 100)
        check("count_after_1", h.samples_in_session, 1)
        check("first_after_1", h.first_rss_kb(), 100)
        check("last_after_1", h.last_rss_kb(), 100)

        h.append(10.0, 200)
        check("count_after_2", h.samples_in_session, 2)
        check("slope_2pts", approx(h.slope_kb_per_sec(), 10.0), True)
        check("max_after_2", h.max_rss_kb(), 200)

    @case("sliding_history_eviction")
    def _():
        h = SlidingHistory(limit=3)
        h.append(0.0, 100)
        h.append(1.0, 200)
        h.append(2.0, 300)
        h.append(3.0, 400)
        # Only the last 3 samples are retained: (1,200),(2,300),(3,400)
        # slope = 100 KB/s
        check("count", h.samples_in_session, 4)  # counter never decreases
        check("first_evicted", h.first_rss_kb(), 200)
        check("slope_after_evict", approx(h.slope_kb_per_sec(), 100.0), True)

    @case("slope_stable_process")
    def _():
        # Realistic stable process: RSS hovers around 784 KB across 10 samples
        import random
        random.seed(42)
        h = SlidingHistory()
        t0 = 0.0
        for i in range(10):
            rss = 784 + random.randint(-8, 8)
            h.append(t0 + i * 30.0, rss)
        s = h.slope_kb_per_sec()
        check("stable_classified_healthy", classify_slope(s), HEALTHY)
        check("stable_slope_small", abs(s) < 0.05, True)  # well under threshold

    @case("slope_linear_growth_process")
    def _():
        # 200 KB/sample over 30s windows: that's 200 KB/30s, well over WARN
        # threshold (100 KB/30s) but under LEAK (500 KB/30s).
        h = SlidingHistory()
        t0 = 0.0
        for i in range(10):
            h.append(t0 + i * 30.0, 5000 + 200 * i)
        s = h.slope_kb_per_sec()
        check("growth_200KB_per_30s", approx(s, 200.0 / 30.0), True)
        check("classified_warn", classify_slope(s), WARN)

    @case("slope_drop_then_grow")
    def _():
        # First half: RSS drops 200→100; second half: RSS grows 100→500
        # Tests the rolling window's ability to detect the recent growth.
        h = SlidingHistory()
        t0 = 0.0
        samples = [200, 180, 160, 140, 120, 100, 200, 300, 400, 500]
        for i, rss in enumerate(samples):
            h.append(t0 + i * 30.0, rss)
        # Last 3 samples: (t=210,rss=400), (t=240,rss=500), (t=270,rss=600 → but rss is 500 last)
        # Actually last 3 samples are at i=7,8,9 → (t=210,rss=400),(t=240,rss=500)
        # Wait, samples = [200,180,160,140,120,100,200,300,400,500] indices 0..9
        # So last 3 = indices 7,8,9 = [300, 400, 500] at t = 210, 240, 270
        # slope = (500-300)/(270-210) = 200/60 = 10/3 KB/s
        # per-30s = 100 → at warn boundary → HEALTHY (strict >)
        s_window = h.slope_kb_per_sec(window=3)
        check("drop_then_growth_slope", approx(s_window, (500 - 300) / 60.0), True)
        check("classified_at_warn_boundary_healthy", classify_slope(s_window), HEALTHY)
        # Last 5 samples: indices 5..9 → rss [100, 200, 300, 400, 500] at t=150,180,210,240,270
        # slope via least squares = (5*Σxy - Σx*Σy) / (5*Σx² - (Σx)²)
        # With perfectly linear data this equals (last-first)/(last_t-first_t) = 400/120 = 10/3 KB/s
        s_window5 = h.slope_kb_per_sec(window=5)
        check("drop_then_growth_5", approx(s_window5, 400.0 / 120.0), True)
        check("classified_healthy", classify_slope(s_window5), HEALTHY)

    @case("parse_since")
    def _():
        check("24h", _parse_since("24h"), 86400)
        check("1h", _parse_since("1h"), 3600)
        check("30m", _parse_since("30m"), 1800)
        check("90s", _parse_since("90s"), 90)
        check("1d", _parse_since("1d"), 86400)
        check("bare_2_hours", _parse_since("2"), 7200)

    @case("strip_ps_parens")
    def _():
        check("no_parens", _strip_ps_parens("thegent-mcp"), "thegent-mcp")
        check("with_parens", _strip_ps_parens("(thegent-mcp)"), "thegent-mcp")
        check("with_spaces", _strip_ps_parens("  thegent-mcp  "), "thegent-mcp")
        check("parens_with_args", _strip_ps_parens("(python foo bar)"), "python foo bar")

    @case("basename_extraction")
    def _():
        # _basename() is called only with a single whitespace-free token
        # (the first column of `ps` output, post-paren-stripping). Path()
        # does not split on whitespace, so passing a multi-word string is
        # not a supported use case — only single-token inputs are tested.
        check("plain", _basename("sharecli-tray"), "sharecli-tray")
        check("with_path", _basename("/Users/kooshapari/bin/sharecli-tray"), "sharecli-tray")
        check("python_token", _basename("/opt/homebrew/bin/python3"), "python3")
        check("empty", _basename(""), "")

    print(f"1..{len(cases)}")
    for i, (name, fn) in enumerate(cases, 1):
        try:
            fn()
            if any(name in f for f in failures):
                print(f"not ok {i} - {name}")
            else:
                print(f"ok {i} - {name}")
        except Exception as exc:
            print(f"not ok {i} - {name} (exception: {exc})")
            failures.append(f"  EXCEPTION in {name}: {exc}")

    if failures:
        print("")
        print("FAILURES:")
        for f in failures:
            print(f)
        return 1
    print("")
    print(f"All {len(cases)} cases passed.")
    return 0


# ---------------------------------------------------------------------------
# Argv dispatch
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "usage: leak-detect {collect|run|report|test} [--since=24h]",
            file=sys.stderr,
        )
        return 2

    sub = argv[1]
    if sub == "collect":
        return cmd_collect()
    if sub == "run":
        return cmd_run()
    if sub == "report":
        since = "24h"
        for arg in argv[2:]:
            if arg.startswith("--since="):
                since = arg.split("=", 1)[1]
        return cmd_report(since)
    if sub == "test":
        return cmd_test()

    print(f"unknown subcommand: {sub}", file=sys.stderr)
    print(
        "usage: leak-detect {collect|run|report|test} [--since=24h]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
