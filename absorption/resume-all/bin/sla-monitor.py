#!/opt/homebrew/bin/python3
"""
sla-monitor.py — Phase F hardening item F09.

Continuously tracks 4 service-level indicators for the resume-all toolkit
and emits alerts when thresholds are breached:

  1. Snapshot freshness      now() - snapshot.jsonl.mtime
                             warn > 60s, critical > 120s
  2. IPC daemon health       round-trip latency of `health.status`
                             warn > 200ms, critical > 1000ms
  3. IPC socket reachable    boolean (sustained thresholds)
                             warn if false for > 30s, critical if false for > 90s
  4. Launchd jobs healthy    count of jobs whose state = running (or runs > 0
                             for periodic jobs)
                             warn if < 4, critical if < 3

Storage
-------
- Metrics  : ~/.local/share/resume-all/sla-metrics.jsonl  (append-only JSONL)
- Alerts   : ~/.local/share/resume-all/sla-alerts.log     (human-readable)
- State    : ~/.local/share/resume-all/sla-state.json     (alert dedup state)

Subcommands
-----------
  collect           poll once, append one JSONL line, skip if last < 5s ago
  run               daemon mode: poll every 30s, alert on threshold breach
  report --since=Nh read JSONL, emit markdown report
  test              inline self-tests (3+ cases: green, warn, critical)

Design notes
------------
- Stdlib only (no new pip deps).
- The poller tolerates the IPC daemon being down (no crash, ipc_reachable=false).
- The poller tolerates any log file or socket missing (graceful degradation).
- Alerts dedupe: if the same alert fires for 3 consecutive polls, only log once
  (in-memory counter + state file for crash survival).
- /opt/homebrew/bin/python3 shebang (Homebrew 3.14.x — see runbook §7).
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LAUNCHD_UID = os.getuid()
LAUNCHD_GUI_DOMAIN = f"gui/{LAUNCHD_UID}"

# Storage paths (under XDG_DATA_HOME-style ~/.local/share)
DATA_DIR = Path.home() / ".local" / "share" / "resume-all"
METRICS_PATH = DATA_DIR / "sla-metrics.jsonl"
ALERTS_PATH = DATA_DIR / "sla-alerts.log"
STATE_PATH = DATA_DIR / "sla-state.json"

# Snapshot file we monitor (the canonical one — matches health-check.py)
SNAPSHOT_PATH = Path.home() / ".local" / "share" / "resume-all" / "snapshot.jsonl"

# Thresholds (seconds for freshness, milliseconds for latency)
SNAPSHOT_WARN_S = 60
SNAPSHOT_CRIT_S = 120
IPC_LATENCY_WARN_MS = 200
IPC_LATENCY_CRIT_MS = 1000
IPC_REACHABLE_WARN_S = 30
IPC_REACHABLE_CRIT_S = 90
LAUNCHD_WARN = 4   # warn if count < 4
LAUNCHD_CRIT = 3   # critical if count < 3

# Polling cadence
DAEMON_INTERVAL_S = 30
COLLECT_MIN_SPACING_S = 5
ALERT_DEDUP_POLLS = 3  # require 3 consecutive breaches before logging

# Launchd jobs to monitor (the canonical 4 from the resume-all plist set)
LAUNCHD_JOBS: tuple[str, ...] = (
    "com.kooshapari.resume-all-snapshot",
    "com.kooshapari.resume-all-ipc",
    "com.kooshapari.resume-all-watch",
    "com.kooshapari.resume-all-zmx",
)

# Verdict levels
GREEN = "green"
WARN = "warn"
CRIT = "critical"


# ---------------------------------------------------------------------------
# Probe: snapshot freshness
# ---------------------------------------------------------------------------

def probe_snapshot_age() -> int | None:
    """Returns snapshot age in seconds, or None if file missing/unreadable."""
    try:
        if not SNAPSHOT_PATH.exists():
            return None
        mtime = SNAPSHOT_PATH.stat().st_mtime
    except OSError:
        return None
    return int(time.time() - mtime)


# ---------------------------------------------------------------------------
# Probe: IPC daemon (NDJSON health.status)
# ---------------------------------------------------------------------------

def _ipc_socket_paths() -> tuple[str, ...]:
    """Resolution order: env override, then macOS-canonical, then Linux-canonical.
    Matches the resolution in sharecli_bridge.py + health-check.py."""
    env = os.environ.get("SHARECLI_IPC_SOCK")
    if env:
        return (env,)
    return (
        os.path.expanduser("~/Library/Application Support/sharecli/ipc.sock"),
        os.path.expanduser("~/.local/share/sharecli/ipc.sock"),
    )


def probe_ipc(timeout_s: float = 5.0) -> dict:
    """Returns dict with:
        reachable (bool), latency_ms (int|None), error (str|None)
    Latency is the round-trip time of `health.status`. If unreachable,
    latency_ms is None and error explains why.
    """
    out: dict[str, Any] = {"reachable": False, "latency_ms": None, "error": None}

    socket_path = None
    for candidate in _ipc_socket_paths():
        if os.path.exists(candidate):
            socket_path = candidate
            break
    if socket_path is None:
        out["error"] = "socket file missing"
        return out

    req_id = uuid.uuid4().int & 0xFFFFFFFF
    request_line = (
        json.dumps(
            {"id": req_id, "method": "health.status", "params": {}},
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    t0 = time.monotonic()
    try:
        sock.settimeout(timeout_s)
        sock.connect(socket_path)
        sock.sendall(request_line)

        buf = b""
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            buf += chunk
            if buf.endswith(b"\n"):
                break
    except (OSError, socket.error, socket.timeout) as exc:
        out["error"] = f"transport: {exc}"
        return out
    finally:
        try:
            sock.close()
        except OSError:
            pass

    elapsed_ms = int((time.monotonic() - t0) * 1000)

    if not buf.strip():
        out["error"] = "empty response"
        return out

    try:
        json.loads(buf.decode("utf-8").strip())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        out["error"] = f"parse: {exc}"
        return out

    out["reachable"] = True
    out["latency_ms"] = elapsed_ms
    return out


# ---------------------------------------------------------------------------
# Probe: launchd jobs
# ---------------------------------------------------------------------------

def probe_launchd_job(label: str) -> dict:
    """Returns dict with: label, state, pid, runs, last_exit_code, healthy, error.

    `healthy` is True if the job is either:
      - state = running (long-lived daemon), OR
      - state = not running AND runs > 0 AND last_exit_code == 0
        (periodic job that ran cleanly between ticks).
    """
    out: dict[str, Any] = {
        "label": label,
        "state": None,
        "pid": None,
        "runs": 0,
        "last_exit_code": None,
        "healthy": False,
        "error": None,
    }
    full_label = f"{LAUNCHD_GUI_DOMAIN}/{label}"
    try:
        proc = subprocess.run(
            ["/bin/launchctl", "print", full_label],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        out["error"] = f"launchctl invocation failed: {exc}"
        return out

    if proc.returncode != 0:
        out["error"] = (
            f"launchctl print returned {proc.returncode}: "
            f"{(proc.stderr or proc.stdout).strip().splitlines()[0] if (proc.stderr or proc.stdout) else ''}"
        )
        return out

    text = proc.stdout

    # Top-level state
    for line in text.splitlines():
        if line.startswith("\tstate = ") or line.startswith("state = "):
            out["state"] = line.split("=", 1)[1].strip()
            break
    if "state = running" not in text and "state = not running" in text:
        out["state"] = "not running"

    # Periodic job run count
    for line in text.splitlines():
        if line.startswith("\truns = "):
            try:
                out["runs"] = int(line.split("=", 1)[1].strip())
            except ValueError:
                pass
            break

    # PID
    for line in text.splitlines():
        line_stripped = line.strip()
        if line_stripped.startswith("pid = "):
            try:
                out["pid"] = int(line_stripped.split("=", 1)[1].strip())
            except ValueError:
                pass
            break

    # Last exit code
    for line in text.splitlines():
        line_stripped = line.strip()
        if line_stripped.startswith("last exit code = "):
            value = line_stripped.split("=", 1)[1].strip()
            try:
                out["last_exit_code"] = int(value)
            except ValueError:
                pass
            break

    # Healthy classification
    if out["state"] == "running":
        out["healthy"] = True
    elif (
        out["state"] == "not running"
        and out["last_exit_code"] == 0
        and out["runs"] > 0
    ):
        out["healthy"] = True
    return out


def probe_all_launchd_jobs() -> list[dict]:
    results = []
    for label in LAUNCHD_JOBS:
        results.append(probe_launchd_job(label))
    return results


def healthy_launchd_count() -> int:
    """Count of launchd jobs that are healthy. Tolerates launchctl failures
    (treats them as unhealthy)."""
    count = 0
    for probe in probe_all_launchd_jobs():
        if probe["healthy"]:
            count += 1
    return count


# ---------------------------------------------------------------------------
# SLI classification (pure functions, easy to test)
# ---------------------------------------------------------------------------

def classify_snapshot(age_s: int | None) -> str:
    if age_s is None:
        return CRIT  # missing snapshot is critical
    if age_s > SNAPSHOT_CRIT_S:
        return CRIT
    if age_s > SNAPSHOT_WARN_S:
        return WARN
    return GREEN


def classify_ipc_latency(latency_ms: int | None, reachable: bool) -> str:
    if not reachable:
        # Latency is undefined when the daemon is down. The `ipc_reachable`
        # SLI (with its duration-based thresholds) is the authoritative signal
        # for the down state. Returning GREEN here keeps the latency verdict
        # meaningful: a non-green latency verdict means "the daemon is up and
        # responding slowly", not "the daemon is down".
        return GREEN
    if latency_ms is None:
        # Defensive: reachable=True but no latency reading. Treat as critical
        # so the discrepancy is surfaced (the daemon replied but we have no
        # timing).
        return CRIT
    if latency_ms > IPC_LATENCY_CRIT_MS:
        return CRIT
    if latency_ms > IPC_LATENCY_WARN_MS:
        return WARN
    return GREEN


def classify_ipc_reachable_duration(down_duration_s: int | None) -> str:
    """Classify based on how long the socket has been down.
    down_duration_s = 0 means reachable, None means never seen reachable.
    """
    if down_duration_s is None:
        return CRIT  # never seen reachable is critical
    if down_duration_s == 0:
        return GREEN
    if down_duration_s > IPC_REACHABLE_CRIT_S:
        return CRIT
    if down_duration_s > IPC_REACHABLE_WARN_S:
        return WARN
    return GREEN


def classify_launchd_count(count: int) -> str:
    if count < LAUNCHD_CRIT:
        return CRIT
    if count < LAUNCHD_WARN:
        return WARN
    return GREEN


def sample_verdicts(
    snapshot_age_s: int | None,
    ipc_latency_ms: int | None,
    ipc_reachable: bool,
    ipc_down_duration_s: int | None,
    launchd_count: int,
) -> dict[str, str]:
    """Compute all 4 verdicts for a sample."""
    return {
        "snapshot": classify_snapshot(snapshot_age_s),
        "ipc_latency": classify_ipc_latency(ipc_latency_ms, ipc_reachable),
        "ipc_reachable": classify_ipc_reachable_duration(ipc_down_duration_s),
        "launchd": classify_launchd_count(launchd_count),
    }


def is_all_green(verdicts: dict[str, str]) -> bool:
    return all(v == GREEN for v in verdicts.values())


# ---------------------------------------------------------------------------
# Sample collection (one-shot poll)
# ---------------------------------------------------------------------------

def collect_sample() -> dict:
    """Poll all 4 SLIs once and return the raw sample dict.

    Does NOT touch the metrics file. Callers (`collect`, `run`) decide when
    to write. This keeps the function pure and easy to test.
    """
    snap_age = probe_snapshot_age()
    ipc = probe_ipc()
    lcount = healthy_launchd_count()

    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ts_epoch": int(time.time()),
        "snapshot_age_s": snap_age,
        "ipc_latency_ms": ipc["latency_ms"],
        "ipc_reachable": ipc["reachable"],
        "launchd_healthy_count": lcount,
    }


def _last_sample_epoch() -> int | None:
    """Read the metrics file and return the ts_epoch of the last sample, or None."""
    try:
        if not METRICS_PATH.exists():
            return None
        last_ts = None
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
    """Poll once, append to JSONL. Skip if last sample < 5s ago."""
    last = _last_sample_epoch()
    now = int(time.time())
    if last is not None and (now - last) < COLLECT_MIN_SPACING_S:
        remaining = COLLECT_MIN_SPACING_S - (now - last)
        print(
            f"skip: last sample {now - last}s ago (min spacing {COLLECT_MIN_SPACING_S}s, "
            f"try again in {remaining}s)",
            file=sys.stderr,
        )
        return 0

    sample = collect_sample()
    append_sample(sample)
    print(json.dumps(sample, separators=(",", ":")))
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
    sample: dict,
    ipc_down_duration_s: int | None,
    state: dict,
) -> list[tuple[str, str]]:
    """Compute list of (alert_key, detail) for any active breaches.
    Updates `state` in-place for dedup. Returns the list of NEW alerts to log
    (those that crossed the dedup threshold for the first time since the last
    clear).
    """
    verdicts = sample_verdicts(
        sample["snapshot_age_s"],
        sample["ipc_latency_ms"],
        sample["ipc_reachable"],
        ipc_down_duration_s,
        sample["launchd_healthy_count"],
    )
    new_alerts: list[tuple[str, str]] = []

    breach_map: list[tuple[str, str, str]] = [
        ("snapshot_stale", verdicts["snapshot"], f"snapshot age {sample['snapshot_age_s']}s"),
        (
            "ipc_latency_high",
            verdicts["ipc_latency"],
            f"ipc latency {sample['ipc_latency_ms']}ms (reachable={sample['ipc_reachable']})",
        ),
        (
            "ipc_unreachable",
            verdicts["ipc_reachable"],
            f"ipc down for {ipc_down_duration_s}s" if ipc_down_duration_s else "ipc down (unknown duration)",
        ),
        (
            "launchd_unhealthy",
            verdicts["launchd"],
            f"only {sample['launchd_healthy_count']}/{len(LAUNCHD_JOBS)} launchd jobs healthy",
        ),
    ]

    for key, verdict, detail in breach_map:
        state_key = f"alert:{key}"
        consec = int(state.get(f"{state_key}:consec", 0))
        logged = bool(state.get(f"{state_key}:logged", False))

        if verdict == GREEN:
            # Cleared — reset counter and log a recovery if we had logged
            if logged:
                _log_alert(f"{key}_recovered", detail)
            state[f"{state_key}:consec"] = 0
            state[f"{state_key}:logged"] = False
            continue

        # In breach (WARN or CRIT)
        consec += 1
        state[f"{state_key}:consec"] = consec
        if consec >= ALERT_DEDUP_POLLS and not logged:
            new_alerts.append((key, f"{verdict}: {detail}"))
            state[f"{state_key}:logged"] = True

    return new_alerts


def cmd_run() -> int:
    """Daemon mode: poll every DAEMON_INTERVAL_S, write metrics, alert on
    threshold breach. Tolerates all errors and keeps running.
    """
    print(
        f"sla-monitor daemon starting (interval={DAEMON_INTERVAL_S}s, "
        f"data_dir={DATA_DIR})",
        file=sys.stderr,
    )

    state = _load_state()
    last_reachable_ts: float | None = None  # epoch seconds of last reachable sample
    # Seed from existing metrics: walk the JSONL tail to find the last reachable sample
    try:
        if METRICS_PATH.exists():
            with METRICS_PATH.open("r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if obj.get("ipc_reachable") is True:
                            last_reachable_ts = float(obj.get("ts_epoch") or 0)
                    except (ValueError, json.JSONDecodeError):
                        continue
    except OSError:
        pass

    try:
        while True:
            sample = collect_sample()
            now = float(sample["ts_epoch"])
            if sample["ipc_reachable"]:
                last_reachable_ts = now

            if last_reachable_ts is None:
                ipc_down_duration_s: int | None = None
            elif sample["ipc_reachable"]:
                ipc_down_duration_s = 0
            else:
                ipc_down_duration_s = int(now - last_reachable_ts)

            append_sample(sample)
            new_alerts = _evaluate_alerts(sample, ipc_down_duration_s, state)
            for key, detail in new_alerts:
                _log_alert(key, detail)

            _save_state(state)

            if new_alerts:
                print(
                    f"[{sample['ts']}] alerts fired: {[(k, d) for k, d in new_alerts]}",
                    file=sys.stderr,
                )

            time.sleep(DAEMON_INTERVAL_S)
    except KeyboardInterrupt:
        print("\nsla-monitor daemon stopped", file=sys.stderr)
        return 0


# ---------------------------------------------------------------------------
# Subcommand: report
# ---------------------------------------------------------------------------

def _parse_since(since_str: str) -> int:
    """Parse a duration string like '24h', '1h', '30m', '90s' to seconds."""
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


def _percentile(values: list[int], p: float) -> int:
    """Linear-interpolation percentile (0 <= p <= 100). Empty list -> 0."""
    if not values:
        return 0
    sorted_v = sorted(values)
    if len(sorted_v) == 1:
        return sorted_v[0]
    k = (p / 100.0) * (len(sorted_v) - 1)
    f = int(k)
    c = min(f + 1, len(sorted_v) - 1)
    if f == c:
        return sorted_v[f]
    return int(sorted_v[f] + (sorted_v[c] - sorted_v[f]) * (k - f))


def _enrich_samples(samples: list[dict]) -> list[tuple[dict, dict[str, str]]]:
    """For each sample, compute ipc_reachable down_duration_s based on
    consecutive samples, then compute the full verdicts dict.

    Returns list of (sample, verdicts) tuples in input order.
    """
    last_reachable_ts: int | None = None
    out: list[tuple[dict, dict[str, str]]] = []
    for s in samples:
        ts = int(s.get("ts_epoch") or 0)
        ipc_reachable = bool(s.get("ipc_reachable"))
        if ipc_reachable:
            last_reachable_ts = ts
        if ipc_reachable:
            down_dur: int | None = 0
        else:
            down_dur = ts - (last_reachable_ts or ts) if last_reachable_ts is not None else None
        verdicts = sample_verdicts(
            s.get("snapshot_age_s"),
            s.get("ipc_latency_ms"),
            ipc_reachable,
            down_dur,
            int(s.get("launchd_healthy_count") or 0),
        )
        out.append((s, verdicts))
    return out


def _compute_incidents(samples: list[dict]) -> list[dict]:
    """Walk samples in order; identify incident periods (any non-green verdict).
    An incident starts when verdicts go from all-green to not-all-green and
    ends when they return to all-green. Reports duration and recovery time.
    """
    enriched = _enrich_samples(samples)
    incidents: list[dict] = []
    in_incident = False
    incident_start: int | None = None
    incident_categories: set[str] = set()
    incident_max_severity: str = GREEN

    for s, verdicts in enriched:
        all_green = is_all_green(verdicts)
        if not all_green:
            if not in_incident:
                in_incident = True
                incident_start = int(s.get("ts_epoch") or 0)
                incident_categories = set()
                incident_max_severity = GREEN
            # Track which categories contributed
            if verdicts["snapshot"] != GREEN:
                incident_categories.add("snapshot_stale")
                if verdicts["snapshot"] == CRIT:
                    incident_max_severity = CRIT
                elif incident_max_severity != CRIT:
                    incident_max_severity = verdicts["snapshot"]
            if verdicts["ipc_latency"] != GREEN:
                incident_categories.add("ipc_latency_high")
                if verdicts["ipc_latency"] == CRIT:
                    incident_max_severity = CRIT
                elif incident_max_severity != CRIT:
                    incident_max_severity = verdicts["ipc_latency"]
            if verdicts["ipc_reachable"] != GREEN:
                incident_categories.add("ipc_unreachable")
                if verdicts["ipc_reachable"] == CRIT:
                    incident_max_severity = CRIT
                elif incident_max_severity != CRIT:
                    incident_max_severity = verdicts["ipc_reachable"]
            if verdicts["launchd"] != GREEN:
                incident_categories.add("launchd_unhealthy")
                if verdicts["launchd"] == CRIT:
                    incident_max_severity = CRIT
                elif incident_max_severity != CRIT:
                    incident_max_severity = verdicts["launchd"]
        else:
            if in_incident:
                incident_end = int(s.get("ts_epoch") or 0)
                incidents.append({
                    "start_epoch": incident_start,
                    "end_epoch": incident_end,
                    "duration_s": incident_end - (incident_start or 0),
                    "max_severity": incident_max_severity,
                    "categories": sorted(incident_categories),
                })
                in_incident = False
                incident_start = None
                incident_categories = set()
                incident_max_severity = GREEN

    if in_incident:
        last_ts = int(samples[-1].get("ts_epoch") or 0) if samples else 0
        incidents.append({
            "start_epoch": incident_start,
            "end_epoch": last_ts,
            "duration_s": last_ts - (incident_start or 0),
            "max_severity": incident_max_severity,
            "categories": sorted(incident_categories),
            "ongoing": True,
        })

    return incidents


def _compute_alert_frequencies(samples: list[dict]) -> dict[str, int]:
    """Count breach samples by category. Per-sample count (not per-incident)."""
    counts: dict[str, int] = {
        "snapshot_stale": 0,
        "ipc_latency_high": 0,
        "ipc_unreachable": 0,
        "launchd_unhealthy": 0,
    }
    for _s, v in _enrich_samples(samples):
        if v["snapshot"] != GREEN:
            counts["snapshot_stale"] += 1
        if v["ipc_latency"] != GREEN:
            counts["ipc_latency_high"] += 1
        if v["ipc_reachable"] != GREEN:
            counts["ipc_unreachable"] += 1
        if v["launchd"] != GREEN:
            counts["launchd_unhealthy"] += 1
    return counts


def _format_ts(epoch: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def cmd_report(since: str) -> int:
    since_s = _parse_since(since)
    now = int(time.time())
    since_epoch = now - since_s
    samples = _read_metrics(since_epoch)

    lines: list[str] = []
    lines.append("# SLA Monitoring Report")
    lines.append("")
    lines.append(f"- Window: since `{since}` ({_format_ts(since_epoch)} → {_format_ts(now)})")
    lines.append(f"- Metrics file: `{METRICS_PATH}`")
    lines.append(f"- Samples: {len(samples)}")

    if not samples:
        lines.append("")
        lines.append("> No samples in this window. Run `sla-monitor collect` or `sla-monitor run`.")
        return _emit_report(lines)

    # Compute per-sample verdicts (with reachable duration from consecutive samples)
    enriched = _enrich_samples(samples)
    sample_verdict_list: list[dict[str, str]] = []
    snap_ages: list[int] = []
    ipc_latencies: list[int] = []
    all_green_count = 0

    for s, v in enriched:
        sample_verdict_list.append(v)
        if is_all_green(v):
            all_green_count += 1
        if isinstance(s.get("snapshot_age_s"), int):
            snap_ages.append(s["snapshot_age_s"])
        if isinstance(s.get("ipc_latency_ms"), int):
            ipc_latencies.append(s["ipc_latency_ms"])

    availability = (all_green_count / len(samples)) * 100.0

    lines.append("")
    lines.append("## Availability")
    lines.append("")
    lines.append(
        f"- All-green samples: **{all_green_count} / {len(samples)}** "
        f"= **{availability:.2f}%**"
    )

    lines.append("")
    lines.append("## Latency / Freshness Percentiles")
    lines.append("")
    lines.append("| Metric | p50 | p95 | p99 | n |")
    lines.append("|---|---|---|---|---|")
    lines.append(
        f"| snapshot_age_s | {_percentile(snap_ages, 50)} | "
        f"{_percentile(snap_ages, 95)} | {_percentile(snap_ages, 99)} | "
        f"{len(snap_ages)} |"
    )
    lines.append(
        f"| ipc_latency_ms | {_percentile(ipc_latencies, 50)} | "
        f"{_percentile(ipc_latencies, 95)} | {_percentile(ipc_latencies, 99)} | "
        f"{len(ipc_latencies)} |"
    )

    # Alert frequency
    freqs = _compute_alert_frequencies(samples)
    sorted_freqs = sorted(freqs.items(), key=lambda kv: -kv[1])

    lines.append("")
    lines.append("## Top 3 Alert Categories")
    lines.append("")
    lines.append("| Rank | Category | Breach samples |")
    lines.append("|---|---|---|")
    for i, (cat, n) in enumerate(sorted_freqs[:3], 1):
        lines.append(f"| {i} | `{cat}` | {n} |")

    # Incidents
    all_incidents = _compute_incidents(samples)

    lines.append("")
    lines.append(f"## Incidents ({len(all_incidents)})")
    lines.append("")
    if not all_incidents:
        lines.append("> No incidents in window.")
    else:
        lines.append("| Start (UTC) | Duration | Severity | Categories | Status |")
        lines.append("|---|---|---|---|---|")
        for inc in all_incidents:
            start_ts = _format_ts(int(inc.get("start_epoch") or 0))
            dur_s = int(inc.get("duration_s") or 0)
            dur_str = (
                f"{dur_s // 60}m{dur_s % 60:02d}s"
                if dur_s >= 60
                else f"{dur_s}s"
            )
            cats = inc.get("categories") or [inc.get("category", "?")]
            ongoing = "ongoing" if inc.get("ongoing") else "recovered"
            lines.append(
                f"| {start_ts} | {dur_str} | **{inc.get('max_severity', '?')}** | "
                f"{', '.join(cats)} | {ongoing} |"
            )

    return _emit_report(lines)


def _emit_report(lines: list[str]) -> int:
    print("\n".join(lines))
    return 0


# ---------------------------------------------------------------------------
# Subcommand: test (inline self-tests)
# ---------------------------------------------------------------------------

def cmd_test() -> int:
    """Run inline self-tests for the classification functions. Prints
    a TAP-like summary and exits 0 on success, 1 on failure."""
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

    @case("green_snapshot_fresh")
    def _():
        check("snapshot(10s)", classify_snapshot(10), GREEN)
        check("snapshot(60s)", classify_snapshot(60), GREEN)
        check("snapshot(0s)", classify_snapshot(0), GREEN)

    @case("warn_snapshot_stale")
    def _():
        check("snapshot(61s)", classify_snapshot(61), WARN)
        check("snapshot(90s)", classify_snapshot(90), WARN)
        check("snapshot(120s)", classify_snapshot(120), WARN)

    @case("critical_snapshot_very_stale")
    def _():
        check("snapshot(121s)", classify_snapshot(121), CRIT)
        check("snapshot(600s)", classify_snapshot(600), CRIT)
        check("snapshot(None)", classify_snapshot(None), CRIT)

    @case("green_ipc_latency")
    def _():
        check("latency(50ms,reachable)", classify_ipc_latency(50, True), GREEN)
        check("latency(200ms,reachable)", classify_ipc_latency(200, True), GREEN)

    @case("warn_ipc_latency")
    def _():
        check("latency(201ms,reachable)", classify_ipc_latency(201, True), WARN)
        check("latency(500ms,reachable)", classify_ipc_latency(500, True), WARN)
        check("latency(1000ms,reachable)", classify_ipc_latency(1000, True), WARN)

    @case("critical_ipc_latency")
    def _():
        check("latency(1001ms,reachable)", classify_ipc_latency(1001, True), CRIT)
        # unreachable → latency is undefined; reachability SLI handles it
        check("latency(None,unreachable)", classify_ipc_latency(None, False), GREEN)

    @case("reachable_duration_thresholds")
    def _():
        check("reachable(0s)", classify_ipc_reachable_duration(0), GREEN)
        check("reachable(30s)", classify_ipc_reachable_duration(30), GREEN)
        check("reachable(31s)", classify_ipc_reachable_duration(31), WARN)
        check("reachable(90s)", classify_ipc_reachable_duration(90), WARN)
        check("reachable(91s)", classify_ipc_reachable_duration(91), CRIT)
        check("reachable(None)", classify_ipc_reachable_duration(None), CRIT)

    @case("launchd_healthy_count")
    def _():
        check("count(4)", classify_launchd_count(4), GREEN)
        check("count(3)", classify_launchd_count(3), WARN)
        check("count(2)", classify_launchd_count(2), CRIT)
        check("count(0)", classify_launchd_count(0), CRIT)

    @case("sample_verdicts_all_green")
    def _():
        v = sample_verdicts(10, 50, True, 0, 4)
        for k, val in v.items():
            check(f"verdicts[{k}]", val, GREEN)
        check("is_all_green", is_all_green(v), True)

    @case("sample_verdicts_mixed")
    def _():
        # stale snapshot (warn), high latency (n/a since unreachable),
        # ipc down 60s (warn), 3 jobs (warn)
        v = sample_verdicts(90, 500, False, 60, 3)
        check("snapshot_warn", v["snapshot"], WARN)
        # latency is GREEN when unreachable (undefined; reachability SLI covers it)
        check("ipc_latency_green_unreachable", v["ipc_latency"], GREEN)
        check("ipc_reachable_warn", v["ipc_reachable"], WARN)
        check("launchd_warn", v["launchd"], WARN)
        check("is_all_green", is_all_green(v), False)

    @case("sample_verdicts_critical")
    def _():
        # very stale snapshot, ipc unreachable, 0 launchd jobs
        v = sample_verdicts(500, None, False, None, 0)
        check("snapshot_crit", v["snapshot"], CRIT)
        # latency is GREEN when unreachable (undefined; reachability SLI covers it)
        check("ipc_latency_green_unreachable", v["ipc_latency"], GREEN)
        check("ipc_reachable_crit", v["ipc_reachable"], CRIT)
        check("launchd_crit", v["launchd"], CRIT)
        check("is_all_green", is_all_green(v), False)

    @case("percentile_basic")
    def _():
        check("p50(1..10)", _percentile(list(range(1, 11)), 50), 5)
        check("p95(1..100)", _percentile(list(range(1, 101)), 95), 95)
        check("p99(1..100)", _percentile(list(range(1, 101)), 99), 99)
        check("p50(empty)", _percentile([], 50), 0)

    @case("parse_since")
    def _():
        check("24h", _parse_since("24h"), 86400)
        check("1h", _parse_since("1h"), 3600)
        check("30m", _parse_since("30m"), 1800)
        check("90s", _parse_since("90s"), 90)
        check("1d", _parse_since("1d"), 86400)

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
            "usage: sla-monitor {collect|run|report|test} [--since=24h]",
            file=sys.stderr,
        )
        return 2

    sub = argv[1]
    if sub == "collect":
        return cmd_collect()
    if sub == "run":
        return cmd_run()
    if sub == "report":
        # Parse --since flag from remaining args
        since = "24h"
        for arg in argv[2:]:
            if arg.startswith("--since="):
                since = arg.split("=", 1)[1]
        return cmd_report(since)
    if sub == "test":
        return cmd_test()

    print(f"unknown subcommand: {sub}", file=sys.stderr)
    print(
        "usage: sla-monitor {collect|run|report|test} [--since=24h]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
