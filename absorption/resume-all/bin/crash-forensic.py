#!/opt/homebrew/bin/python3
"""
crash-forensic.py — Phase F hardening item F02.

Crash-forensic analysis tool for the resume-all toolkit. Given a time
window (default 24h), parses the eight launchd-managed log files plus the
system launchd log and produces a human-readable timeline showing what
happened during crashes/restarts and what the root cause likely was.

Outputs are three formats:
  * markdown (default) — human-friendly with sections + tables
  * text              — plain text with fixed-width sections
  * json              — machine-readable, includes all raw events

Crash taxonomy (matches the runbook naming):
  * CRASH                 — process exited unexpectedly (non-zero exit OR
                             SIGTERM/SIGKILL/segfault from launchd)
  * RESTART               — launchd spawned a new PID (KeepAlive)
  * BACKEND_LOST          — "no Ghostty/tmux backend" detected
  * WALKER_FAIL           — procs walker timeout / failure
  * IPC_UNREACHABLE       — connection refused / socket unreachable
  * SNAPSHOT_STALE        — snapshot.jsonl mtime > 90s
  * SUCCESS               — tick completed, snapshot written, IPC OK

Constraints honoured:
  * stdlib only (re, datetime, json, sys, argparse, pathlib, collections)
  * Tolerates missing log files (skip with a note)
  * Reads LAST 1 MiB per log file (newer is more relevant)
  * Falls back to file mtime when a line has no recognisable timestamp
  * /opt/homebrew/bin/python3 shebang
  * Executable

Usage:
    crash-forensic.py [--since 24h|2h|7d|...] [--format text|json|markdown]
    crash-forensic.py --self-test
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LOG_DIR = Path.home() / "Library" / "Logs" / "resume-all"
LAUNCHD_SYSTEM_LOG = Path("/var/log/com.apple.xpc.launchd/launchd.log")
SNAPSHOT_FILE = Path.home() / ".local" / "share" / "resume-all" / "snapshot.jsonl"
SNAPSHOT_STALE_SECONDS = 90  # runbook §2 threshold
MAX_LOG_BYTES = 1024 * 1024  # read last 1 MiB per log

# The eight logs the tool scours. (label, path, source_kind)
# source_kind is one of: "zsh_prefix", "iso", "iso_no_label", "bare"
#   zsh_prefix  — snapshot/zmx/watch logs (zsh writes "YYYY-MM-DD HH:MM:SS "
#                 prefix); in practice these logs are bare (no timestamps).
#   iso         — launchd system log + ipc.out.log lines that contain
#                 "sharecli-ipc-daemon ... listening on ..."
#   bare        — fallback: every line attributed to file mtime
LOG_SOURCES: tuple[tuple[str, Path, str], ...] = (
    ("snapshot.err", LOG_DIR / "snapshot.err.log", "zsh_prefix"),
    ("snapshot.out", LOG_DIR / "snapshot.out.log", "zsh_prefix"),
    ("ipc.err",      LOG_DIR / "ipc.err.log", "bare"),
    ("ipc.out",      LOG_DIR / "ipc.out.log", "bare"),
    ("watch.err",    LOG_DIR / "watch.err.log", "zsh_prefix"),
    ("watch.out",    LOG_DIR / "watch.out.log", "zsh_prefix"),
    ("zmx.err",      LOG_DIR / "zmx.err.log", "zsh_prefix"),
    ("zmx.out",      LOG_DIR / "zmx.out.log", "zsh_prefix"),
)

# Additional launchd log (system). We only scan the last 1 MiB; the
# historical file is large and we only need recent events.
LAUNCHD_LOG_SOURCE: tuple[str, Path, str] = ("launchd", LAUNCHD_SYSTEM_LOG, "iso")

# Patient labels for the keepalive-restart pattern detect.
RESUME_ALL_LABELS = (
    "com.kooshapari.resume-all-snapshot",
    "com.kooshapari.resume-all-ipc",
    "com.kooshapari.resume-all-watch",
    "com.kooshapari.resume-all-zmx",
)

# ---------------------------------------------------------------------------
# Timestamp parsing
# ---------------------------------------------------------------------------

# zsh-script style: "2026-08-07 02:46:21 session-snapshot: ..."
ZSH_PREFIX_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+(?P<rest>.*)$"
)

# launchd-style: "2026-08-07 02:46:21.676795 (gui/501/...) <Notice>: ..."
LAUNCHD_PREFIX_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+(?P<rest>.*)$"
)


def _parse_zsh_timestamp(raw: str) -> datetime | None:
    """Parse 'YYYY-MM-DD HH:MM:SS[.ffffff]' (assumed local time)."""
    raw = raw.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def parse_line_timestamp(line: str, file_mtime: datetime, source_kind: str) -> datetime:
    """Return the best timestamp we can extract for a line.

    `source_kind` hints at which prefix shape to try first. If no
    recognisable prefix is present, fall back to file mtime.
    """
    stripped = line.rstrip("\n")
    for pattern in (ZSH_PREFIX_RE, LAUNCHD_PREFIX_RE):
        m = pattern.match(stripped)
        if m:
            parsed = _parse_zsh_timestamp(m.group("ts"))
            if parsed is not None:
                return parsed
    return file_mtime


# ---------------------------------------------------------------------------
# Event classification
# ---------------------------------------------------------------------------

# Patterns that map raw lines to event categories. The order matters:
# rules are evaluated top-down; the FIRST hit wins. We add a priority
# field so we can disambiguate "this looks like a warning but actually
# belongs to a crash" cases.
#
# Patterns are compiled once at module import time.
def _compile(rx: str) -> re.Pattern:
    return re.compile(rx, re.IGNORECASE)


PATTERNS: list[tuple[str, re.Pattern, str, int]] = [
    # CRASH: process exited unexpectedly (non-zero OR signal)
    ("CRASH", _compile(
        r"exited due to (SIG(TERM|KILL|SEGV|BUS|ABRT|ILL|FPE)|signal|signal \d+|"
        r"abort\(\)|segfault|abort)"
    ), "process exited unexpectedly (signal)", 100),
    ("CRASH", _compile(
        r"exited due to exit\(\d+\)" # specific non-zero filtering in classifier
    ), "process exited", 90),
    ("CRASH", _compile(
        r"(Traceback \(most recent call last\)|"
        r"fatal:|panic:|abort trap|EXC_BAD_ACCESS|"
        r"segmentation fault)"
    ), "crash/traceback/panic", 95),
    ("RESTART", _compile(
        r"(xpcproxy spawned with pid|xpcproxy spawned pid|"
        r"service spawn succeeded|"
        r"service state: running.*\[\d+\]|"
        r"launching: instance|"
        r"service state: spawning.*\[)"
    ), "launchd spawned new instance", 80),
    ("BACKEND_LOST", _compile(
        r"no Ghostty/tmux backend detected"
    ), "no Ghostty/tmux backend", 70),
    ("WALKER_FAIL", _compile(
        r"procs walker failed|"
        r"walker failed.*timed out|"
        r"Command '\['/opt/homebrew/bin/procs'.*timed out|"
        r"zig walker failed|"
        r"timeout.*walker"
    ), "walker failure/timeout", 70),
    ("IPC_UNREACHABLE", _compile(
        r"Connection refused|"
        r"socket-unreachable|"
        r"transport: \[Errno 61\]|"
        r"transport: \[Errno 111\]|"
        r"ENOENT.*ipc\.sock|"
        r"ConnectionResetError|"
        r"ECONNREFUSED"
    ), "IPC unreachable", 70),
    ("SUCCESS", _compile(
        r"snapshot: \d+ rows.*live panes|"
        r"successful tick|"
        r"tick.*complete|"
        r"snapshot written|"
        r"sharecli-tray: available"
    ), "snapshot tick succeeded", 30),
]

# launchd KeepAlive pattern: a "state = running, pid = N" or "service state:
# running" line within a few seconds of a CRASH for the same label. We
# treat consecutive launchd lines for the same label where one is a CRASH
# and the next non-EXITED event is a RUNNING spawn as a paired
# CRASH -> RESTART event pair (for MTTR computation).
LAUNCHD_RUNNING_RE = _compile(
    r"\(gui/\d+/(?P<label>[^)]+?)\)\s*<Notice>:\s*service state: running"
)
LAUNCHD_SPAWN_RE = _compile(
    r"\(gui/\d+/(?P<label>[^)]+?)\).*xpcproxy spawned with pid (?P<pid>\d+)"
)
LAUNCHD_LABEL_RE = re.compile(r"\(gui/\d+/(?P<label>[^)]+?)\)")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Event:
    """One classified event."""
    category: str
    detail: str
    source: str
    line: str
    timestamp: datetime

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "detail": self.detail,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "line": self.line[:500],  # cap display length
        }


@dataclass
class CategorySummary:
    """Aggregate stats for one category."""
    category: str
    count: int = 0
    first: datetime | None = None
    last: datetime | None = None
    samples: list[Event] = field(default_factory=list)

    def add(self, event: Event) -> None:
        self.count += 1
        if self.first is None or event.timestamp < self.first:
            self.first = event.timestamp
        if self.last is None or event.timestamp > self.last:
            self.last = event.timestamp
        if len(self.samples) < 3:
            self.samples.append(event)

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "count": self.count,
            "first": self.first.isoformat() if self.first else None,
            "last": self.last.isoformat() if self.last else None,
            "samples": [s.to_dict() for s in self.samples],
        }


# ---------------------------------------------------------------------------
# Log reading
# ---------------------------------------------------------------------------

def _tail_read(path: Path, max_bytes: int) -> tuple[str, float]:
    """Read at most the last `max_bytes` of `path`. Returns (text, mtime)."""
    if not path.exists():
        return ("", 0.0)
    try:
        size = path.stat().st_size
        mtime = path.stat().st_mtime
        offset = max(0, size - max_bytes)
        with path.open("rb") as fh:
            if offset > 0:
                fh.seek(offset)
                # Drop the first (likely partial) line
                fh.readline()
            data = fh.read()
        return (data.decode("utf-8", errors="replace"), mtime)
    except OSError:
        return ("", 0.0)


def _classify_line(line: str) -> tuple[str, str] | None:
    """Return (category, detail) for a line, or None to skip."""
    if not line.strip():
        return None
    for category, pattern, detail, _prio in PATTERNS:
        if pattern.search(line):
            # Special case: bare "exited due to exit(0)" is NOT a crash
            # (it is the expected normal exit for periodic jobs).
            if category == "CRASH" and "exited due to exit(0)" in line:
                continue
            return (category, detail)
    return None


def _scan_log(label: str, path: Path, source_kind: str,
              cutoff: datetime, now: datetime) -> list[Event]:
    """Scan a single log file. Returns events in the window."""
    text, mtime = _tail_read(path, MAX_LOG_BYTES)
    if not text:
        return []
    file_mtime = datetime.fromtimestamp(mtime, tz=timezone.utc)
    events: list[Event] = []
    for line in text.splitlines():
        ts = parse_line_timestamp(line, file_mtime, source_kind)
        if ts < cutoff or ts > now:
            continue
        cls = _classify_line(line)
        if cls is None:
            continue
        category, detail = cls
        events.append(Event(
            category=category,
            detail=detail,
            source=label,
            line=line,
            timestamp=ts,
        ))
    return events


def _scan_launchd_log(path: Path, cutoff: datetime, now: datetime) -> list[Event]:
    """Scan the system launchd log for resume-all events."""
    text, mtime = _tail_read(path, MAX_LOG_BYTES)
    if not text:
        return []
    file_mtime = datetime.fromtimestamp(mtime, tz=timezone.utc)
    events: list[Event] = []
    for line in text.splitlines():
        # Light filter: only keep lines that mention a resume-all label
        # OR signal-style lines. This is the high-volume launchd log and
        # we want to avoid wasted categorization on unrelated services.
        if not any(lbl in line for lbl in RESUME_ALL_LABELS):
            continue
        ts = parse_line_timestamp(line, file_mtime, "iso")
        if ts < cutoff or ts > now:
            continue
        cls = _classify_line(line)
        if cls is None:
            continue
        category, detail = cls
        events.append(Event(
            category=category,
            detail=detail,
            source="launchd",
            line=line,
            timestamp=ts,
        ))
    return events


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def collect_events(cutoff: datetime, now: datetime) -> list[Event]:
    """Run all log scanners. Returns combined event list."""
    events: list[Event] = []
    missing: list[str] = []
    for label, path, kind in LOG_SOURCES:
        if not path.exists():
            missing.append(f"{label} ({path})")
            continue
        events.extend(_scan_log(label, path, kind, cutoff, now))
    if LAUNCHD_SYSTEM_LOG.exists() and _is_readable(LAUNCHD_SYSTEM_LOG):
        events.extend(_scan_launchd_log(LAUNCHD_SYSTEM_LOG, cutoff, now))
    elif LAUNCHD_SYSTEM_LOG.exists():
        missing.append(f"launchd ({LAUNCHD_SYSTEM_LOG}) — not readable")
    else:
        missing.append(f"launchd ({LAUNCHD_SYSTEM_LOG}) — missing")
    events.sort(key=lambda e: e.timestamp)
    return events


def _is_readable(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            fh.read(1)
        return True
    except (PermissionError, OSError):
        return False


def summarize(events: list[Event]) -> dict[str, CategorySummary]:
    """Group events by category and produce summaries."""
    summaries: dict[str, CategorySummary] = {}
    for ev in events:
        s = summaries.setdefault(ev.category, CategorySummary(ev.category))
        s.add(ev)
    return summaries


def compute_mttr(events: list[Event]) -> tuple[float | None, int]:
    """Mean Time To Recovery: average gap between a CRASH and the next
    RESTART in the same source. Returns (seconds, n_pairs)."""
    # Pair CRASH -> RESTART for the same label when launchd reports them.
    # We assume both events are in chronological order.
    crashes = [e for e in events if e.category == "CRASH"]
    restarts = [e for e in events if e.category == "RESTART"]
    if not crashes or not restarts:
        return (None, 0)
    gaps: list[float] = []
    for c in crashes:
        for r in restarts:
            if r.timestamp > c.timestamp and r.source == c.source:
                delta = (r.timestamp - c.timestamp).total_seconds()
                if delta < 600:  # only count plausible recoveries (within 10 min)
                    gaps.append(delta)
                    break
    if not gaps:
        return (None, 0)
    return (sum(gaps) / len(gaps), len(gaps))


def snapshot_age(now: datetime) -> tuple[int | None, str]:
    """Return (age_seconds, freshness) where freshness is fresh|stale|missing."""
    if not SNAPSHOT_FILE.exists():
        return (None, "missing")
    mtime = SNAPSHOT_FILE.stat().st_mtime
    age = int(now.timestamp() - mtime)
    return (age, "fresh" if age <= SNAPSHOT_STALE_SECONDS else "stale")


def verdict(summaries: dict[str, CategorySummary],
            mttr: tuple[float | None, int],
            snap: tuple[int | None, str],
            events: list[Event]) -> str:
    """Return HEALTHY | DEGRADED — <reason> | BROKEN — <reason>."""
    crashes = summaries.get("CRASH", CategorySummary("CRASH")).count
    walker_fails = summaries.get("WALKER_FAIL", CategorySummary("WALKER_FAIL")).count
    ipc_unreached = summaries.get("IPC_UNREACHABLE", CategorySummary("IPC_UNREACHABLE")).count
    backend_lost = summaries.get("BACKEND_LOST", CategorySummary("BACKEND_LOST")).count
    successes = summaries.get("SUCCESS", CategorySummary("SUCCESS")).count

    # Snapshot file is the canonical freshness signal
    snap_age, snap_state = snap
    if snap_state == "missing":
        return "BROKEN — snapshot.jsonl missing"
    if snap_state == "stale":
        return f"DEGRADED — snapshot stale ({snap_age}s > 90s threshold)"

    # No crashes and an active success stream -> HEALTHY
    if crashes == 0 and successes > 0:
        return "HEALTHY"

    # Crashes but follow-up restart events present -> DEGRADED
    if crashes > 0 and summaries.get("RESTART", CategorySummary("RESTART")).count > 0:
        return f"DEGRADED — {crashes} crash(es) with KeepAlive recovery"

    # Crashes with no follow-up -> BROKEN
    if crashes > 0:
        return f"BROKEN — {crashes} crash(es) and no restart within window"

    # IPC unreachable repeatedly but no crashes -> DEGRADED
    if ipc_unreached >= 3:
        return f"DEGRADED — IPC unreachable {ipc_unreached} times"

    # Walker failures repeatedly -> DEGRADED
    if walker_fails >= 3:
        return f"DEGRADED — walker failed {walker_fails} times"

    # No events at all -> suspicious but not necessarily broken
    if not events:
        return "DEGRADED — no events captured in window"

    return "DEGRADED — investigate event log"


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

CATEGORY_ORDER = (
    "CRASH", "RESTART", "BACKEND_LOST", "WALKER_FAIL",
    "IPC_UNREACHABLE", "SNAPSHOT_STALE", "SUCCESS",
)


def _format_ts(ts: datetime | None) -> str:
    if ts is None:
        return "—"
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.1f}h"


def _event_to_row(ev: Event) -> str:
    return f"[{ev.timestamp.strftime('%H:%M:%S')}] {ev.source}: {ev.line.strip()[:200]}"


def render_markdown(summaries: dict[str, CategorySummary],
                    events: list[Event],
                    mttr: tuple[float | None, int],
                    snap: tuple[int | None, str],
                    verdict_str: str,
                    cutoff: datetime, now: datetime,
                    missing: list[str]) -> str:
    out: list[str] = []
    out.append(f"# crash-forensic report")
    out.append("")
    out.append(f"- window: `{_format_ts(cutoff)}` → `{_format_ts(now)}`")
    out.append(f"- total events: {len(events)}")
    snap_age, snap_state = snap
    if snap_age is not None:
        out.append(f"- snapshot.jsonl: {snap_state} (mtime {snap_age}s ago)")
    else:
        out.append(f"- snapshot.jsonl: {snap_state}")
    mttr_s, n_pairs = mttr
    if mttr_s is not None:
        out.append(f"- mean time to recovery: {_format_duration(mttr_s)} (n={n_pairs})")
    else:
        out.append(f"- mean time to recovery: — (no CRASH→RESTART pairs)")
    out.append("")
    out.append(f"## verdict: **{verdict_str}**")
    out.append("")
    if missing:
        out.append("### notes")
        for m in missing:
            out.append(f"- skipped: {m}")
        out.append("")

    # Per-category breakdown
    out.append("## event categories")
    out.append("")
    out.append("| category | count | first | last |")
    out.append("|---|---:|---|---|")
    for cat in CATEGORY_ORDER:
        s = summaries.get(cat)
        if s is None or s.count == 0:
            continue
        out.append(f"| {cat} | {s.count} | {_format_ts(s.first)} | {_format_ts(s.last)} |")
    # Any custom categories we didn't anticipate
    for cat, s in summaries.items():
        if cat in CATEGORY_ORDER:
            continue
        if s.count == 0:
            continue
        out.append(f"| {cat} | {s.count} | {_format_ts(s.first)} | {_format_ts(s.last)} |")
    out.append("")

    # Top three failure modes
    out.append("## top failure modes")
    failure_categories = [c for c in CATEGORY_ORDER if c != "SUCCESS"]
    top = sorted(
        (summaries[c] for c in failure_categories if c in summaries),
        key=lambda s: s.count,
        reverse=True,
    )[:3]
    if top:
        out.append("| # | category | count |")
        out.append("|---|---|---:|")
        for i, s in enumerate(top, 1):
            out.append(f"| {i} | {s.category} | {s.count} |")
    else:
        out.append("_no failure modes detected in window_")
    out.append("")

    # Sample lines per category
    out.append("## samples")
    for cat in CATEGORY_ORDER:
        s = summaries.get(cat)
        if s is None or s.count == 0:
            continue
        out.append("")
        out.append(f"### {cat} ({s.count})")
        for ev in s.samples:
            out.append(f"- `{_format_ts(ev.timestamp)}` {ev.source}: `{ev.line.strip()[:200]}`")
    out.append("")

    # Timeline (last 30 events)
    out.append("## timeline (most recent 30)")
    for ev in events[-30:]:
        out.append(f"- `{_format_ts(ev.timestamp)}` **{ev.category}** [{ev.source}] {_event_to_row(ev)}")
    out.append("")
    return "\n".join(out)


def render_text(summaries: dict[str, CategorySummary],
                events: list[Event],
                mttr: tuple[float | None, int],
                snap: tuple[int | None, str],
                verdict_str: str,
                cutoff: datetime, now: datetime,
                missing: list[str]) -> str:
    out: list[str] = []
    out.append("crash-forensic report")
    out.append("=" * 60)
    out.append(f"window:      {_format_ts(cutoff)} -> {_format_ts(now)}")
    out.append(f"total events: {len(events)}")
    snap_age, snap_state = snap
    if snap_age is not None:
        out.append(f"snapshot:    {snap_state} ({snap_age}s ago)")
    else:
        out.append(f"snapshot:    {snap_state}")
    mttr_s, n_pairs = mttr
    if mttr_s is not None:
        out.append(f"MTTR:        {_format_duration(mttr_s)} (n={n_pairs})")
    else:
        out.append(f"MTTR:        - (no CRASH->RESTART pairs)")
    out.append("")
    out.append(f"verdict:     {verdict_str}")
    out.append("")
    if missing:
        out.append("notes:")
        for m in missing:
            out.append(f"  - skipped: {m}")
        out.append("")

    out.append("event categories")
    out.append("-" * 60)
    for cat in CATEGORY_ORDER:
        s = summaries.get(cat)
        if s is None or s.count == 0:
            continue
        out.append(f"  {cat:<18} count={s.count:<5}  first={_format_ts(s.first)}  last={_format_ts(s.last)}")
    for cat, s in summaries.items():
        if cat in CATEGORY_ORDER:
            continue
        if s.count == 0:
            continue
        out.append(f"  {cat:<18} count={s.count:<5}  first={_format_ts(s.first)}  last={_format_ts(s.last)}")
    out.append("")

    out.append("samples")
    out.append("-" * 60)
    for cat in CATEGORY_ORDER:
        s = summaries.get(cat)
        if s is None or s.count == 0:
            continue
        out.append(f"[{cat}] {s.count} occurrence(s)")
        for ev in s.samples:
            out.append(f"  {_format_ts(ev.timestamp)} {ev.source}: {ev.line.strip()[:200]}")
        out.append("")

    out.append("timeline (most recent 30 events)")
    out.append("-" * 60)
    for ev in events[-30:]:
        out.append(f"  {_format_ts(ev.timestamp)} {ev.category:<18} {ev.source}: {ev.line.strip()[:160]}")
    out.append("")
    return "\n".join(out)


def render_json(summaries: dict[str, CategorySummary],
                events: list[Event],
                mttr: tuple[float | None, int],
                snap: tuple[int | None, str],
                verdict_str: str,
                cutoff: datetime, now: datetime,
                missing: list[str]) -> str:
    payload = {
        "window": {
            "start": cutoff.isoformat(),
            "end": now.isoformat(),
        },
        "verdict": verdict_str,
        "snapshot": {"state": snap[1], "age_seconds": snap[0]},
        "mttr": {"seconds": mttr[0], "pairs": mttr[1]},
        "total_events": len(events),
        "categories": [s.to_dict() for s in summaries.values()],
        "events": [e.to_dict() for e in events],
        "missing": missing,
    }
    return json.dumps(payload, indent=2, sort_keys=True)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_since(raw: str) -> timedelta:
    """Parse a "<int><h|m|d|s>" string into a timedelta."""
    m = re.match(r"^(\d+)([smhd])$", raw.strip().lower())
    if not m:
        raise ValueError(f"invalid --since value: {raw!r} (expected e.g. 24h, 2h, 7d, 90m, 3600s)")
    n = int(m.group(1))
    unit = m.group(2)
    if unit == "s":
        return timedelta(seconds=n)
    if unit == "m":
        return timedelta(minutes=n)
    if unit == "h":
        return timedelta(hours=n)
    if unit == "d":
        return timedelta(days=n)
    raise ValueError(f"invalid --since unit: {unit}")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="crash-forensic",
        description="Crash-forensic analysis for the resume-all toolkit.",
    )
    p.add_argument(
        "--since",
        default="24h",
        help="Time window to analyze (e.g. 24h, 2h, 7d, 90m, 3600s). Default: 24h",
    )
    p.add_argument(
        "--format",
        choices=("text", "json", "markdown"),
        default="markdown",
        help="Output format. Default: markdown",
    )
    p.add_argument(
        "--self-test",
        action="store_true",
        help="Run inline self-tests and exit.",
    )
    return p


# ---------------------------------------------------------------------------
# Self-tests
# ---------------------------------------------------------------------------

def _selftest() -> int:
    """Inline self-tests. Returns 0 on PASS, 1 on FAIL."""
    print("crash-forensic self-test: running...")

    # Test 1: empty logs -> no events, safe to score
    print("  [1] empty logs -> no events")
    summaries = summarize([])
    assert len(summaries) == 0, "expected empty summaries"
    snap = snapshot_age(datetime.now(tz=timezone.utc))
    v = verdict(summaries, (None, 0), snap, [])
    assert v.startswith("DEGRADED") or v.startswith("BROKEN"), f"unexpected verdict: {v}"
    print("    ok")

    # Test 2: single crash + recovery -> MTTR computed
    print("  [2] single crash + recovery -> MTTR computed")
    now = datetime.now(tz=timezone.utc)
    crash = Event(
        category="CRASH",
        detail="segfault",
        source="launchd",
        line="exited due to SIGTERM | sent by launchd[1]",
        timestamp=now - timedelta(seconds=60),
    )
    restart = Event(
        category="RESTART",
        detail="spawned",
        source="launchd",
        line="xpcproxy spawned with pid 12345",
        timestamp=now - timedelta(seconds=50),
    )
    events = [crash, restart]
    summaries = summarize(events)
    assert summaries["CRASH"].count == 1
    assert summaries["RESTART"].count == 1
    mttr, n = compute_mttr(events)
    assert mttr is not None and abs(mttr - 10.0) < 0.01, f"expected MTTR=10s, got {mttr}"
    assert n == 1
    print("    ok")

    # Test 3: multi-event classification respects priority
    print("  [3] multi-event classification")
    walker = Event(
        category="WALKER_FAIL",
        detail="walker timeout",
        source="snapshot.err",
        line="procs walker failed: Command '['/opt/homebrew/bin/procs', '--json']' timed out after 10 seconds",
        timestamp=now - timedelta(seconds=30),
    )
    backend = Event(
        category="BACKEND_LOST",
        detail="no backend",
        source="snapshot.err",
        line="no Ghostty/tmux backend detected; falling back to walker anyway",
        timestamp=now - timedelta(seconds=20),
    )
    unreachable = Event(
        category="IPC_UNREACHABLE",
        detail="socket unreachable",
        source="snapshot.err",
        line="sharecli-tray: unavailable (socket='...', reachable=False, error='socket-unreachable')",
        timestamp=now - timedelta(seconds=10),
    )
    success = Event(
        category="SUCCESS",
        detail="snapshot tick",
        source="snapshot.err",
        line="snapshot: 78 rows, 71 live panes, 8 argv-sids on ghostty",
        timestamp=now - timedelta(seconds=5),
    )
    events = [walker, backend, unreachable, success]
    summaries = summarize(events)
    cats = sorted(summaries.keys())
    assert cats == sorted(["WALKER_FAIL", "BACKEND_LOST", "IPC_UNREACHABLE", "SUCCESS"]), f"got {cats}"
    assert summaries["SUCCESS"].count == 1
    assert summaries["WALKER_FAIL"].count == 1
    print("    ok")

    # Test 4: timestamp parsing
    print("  [4] timestamp parsing")
    ts = parse_line_timestamp(
        "2026-08-07 02:46:21.123456 some message",
        datetime.fromtimestamp(0, tz=timezone.utc),
        "iso",
    )
    assert ts.year == 2026 and ts.month == 8 and ts.day == 7, f"got {ts}"
    # Fallback to file mtime
    fb = parse_line_timestamp(
        "no timestamp here",
        datetime.fromtimestamp(1000000, tz=timezone.utc),
        "bare",
    )
    assert fb.timestamp() == 1000000, f"got {fb}"
    print("    ok")

    # Test 5: --since parsing
    print("  [5] --since parsing")
    assert _parse_since("24h") == timedelta(hours=24)
    assert _parse_since("2h") == timedelta(hours=2)
    assert _parse_since("7d") == timedelta(days=7)
    assert _parse_since("90m") == timedelta(minutes=90)
    assert _parse_since("3600s") == timedelta(seconds=3600)
    try:
        _parse_since("invalid")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    print("    ok")

    # Test 6: missing files don't crash _scan_log
    print("  [6] missing files handled gracefully")
    events = _scan_log("missing", Path("/tmp/does-not-exist-12345"), "bare",
                       now - timedelta(hours=1), now)
    assert events == [], f"expected empty list, got {events}"
    print("    ok")

    print("crash-forensic self-test: PASS")
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.self_test:
        try:
            return _selftest()
        except AssertionError as exc:
            print(f"crash-forensic self-test: FAIL ({exc})", file=sys.stderr)
            return 1

    try:
        window = _parse_since(args.since)
    except ValueError as exc:
        print(f"crash-forensic: {exc}", file=sys.stderr)
        return 2

    now = datetime.now(tz=timezone.utc)
    cutoff = now - window

    events = collect_events(cutoff, now)
    summaries = summarize(events)
    mttr = compute_mttr(events)
    snap = snapshot_age(now)

    # We track "missing" notes separately for reports
    missing: list[str] = []
    for label, path, _kind in LOG_SOURCES:
        if not path.exists():
            missing.append(f"{label} ({path})")
    if not LAUNCHD_SYSTEM_LOG.exists():
        missing.append(f"launchd ({LAUNCHD_SYSTEM_LOG})")
    elif not _is_readable(LAUNCHD_SYSTEM_LOG):
        missing.append(f"launchd ({LAUNCHD_SYSTEM_LOG}) - not readable")

    verdict_str = verdict(summaries, mttr, snap, events)

    if args.format == "json":
        out = render_json(summaries, events, mttr, snap, verdict_str, cutoff, now, missing)
    elif args.format == "text":
        out = render_text(summaries, events, mttr, snap, verdict_str, cutoff, now, missing)
    else:
        out = render_markdown(summaries, events, mttr, snap, verdict_str, cutoff, now, missing)

    sys.stdout.write(out)
    if not out.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
