"""Wastage detection: overlap, duplicate reads, token burn without motion."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from traces.motion import motion_roi


@dataclass
class WastageReport:
    """Aggregate wastage metrics for a run (overlap, giant calls, motion)."""

    generated_at: str
    total_events: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cache_read: int = 0
    giant_calls_32k_plus: int = 0
    duplicate_context_clusters: int = 0
    overlap_waste_rate: float = 0.0
    motion: dict[str, Any] = field(default_factory=dict)
    by_source: dict[str, int] = field(default_factory=dict)
    by_provider: dict[str, int] = field(default_factory=dict)
    top_waste_patterns: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the WastageReport to a JSON-friendly dict."""
        return {
            "generated_at": self.generated_at,
            "total_events": self.total_events,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "total_cache_read": self.total_cache_read,
            "giant_calls_32k_plus": self.giant_calls_32k_plus,
            "duplicate_context_clusters": self.duplicate_context_clusters,
            "overlap_waste_rate": self.overlap_waste_rate,
            "motion": self.motion,
            "by_source": self.by_source,
            "by_provider": self.by_provider,
            "top_waste_patterns": self.top_waste_patterns,
            "recommendations": self.recommendations,
        }


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def analyze_wastage(events: list[dict[str, Any]]) -> WastageReport:
    """Build a WastageReport from a list of trace events (detect overlap + giant calls)."""
    report = WastageReport(generated_at=datetime.now(UTC).isoformat())
    report.total_events = len(events)
    if not events:
        return report

    context_buckets: dict[int, list[str]] = defaultdict(list)
    provider_tokens: Counter[str] = Counter()

    for ev in events:
        tin = int(ev.get("tokens_in") or 0)
        tout = int(ev.get("tokens_out") or 0)
        cache = int(ev.get("tokens_cache_read") or 0)
        report.total_tokens_in += tin
        report.total_tokens_out += tout
        report.total_cache_read += cache
        if tin >= 32768:
            report.giant_calls_32k_plus += 1
        src = ev.get("source") or "unknown"
        report.by_source[src] = report.by_source.get(src, 0) + 1
        prov = ev.get("provider") or "unknown"
        provider_tokens[prov] += tin + tout
        bucket = (tin // 4096) * 4096
        context_buckets[bucket].append(ev.get("session_id") or "")

    report.by_provider = dict(provider_tokens.most_common(20))
    dup_clusters = sum(1 for ids in context_buckets.values() if len(ids) > 3)
    report.duplicate_context_clusters = dup_clusters
    omniroute = [e for e in events if e.get("source") == "omniroute"]
    if omniroute:
        report.overlap_waste_rate = round(dup_clusters / max(len(omniroute), 1), 4)
    report.motion = motion_roi(omniroute or events)

    if report.giant_calls_32k_plus > 0:
        pct = 100 * report.giant_calls_32k_plus / max(report.total_events, 1)
        report.top_waste_patterns.append(
            {
                "pattern": "giant_context_calls",
                "count": report.giant_calls_32k_plus,
                "pct": round(pct, 2),
            }
        )
        report.recommendations.append(
            "Enable Needle context compiler before cloud escalation (>32k avg input)."
        )
    if report.overlap_waste_rate > 0.15:
        report.recommendations.append(
            "High duplicate-context clusters — dedupe parallel forge/codex lanes."
        )
    if report.motion.get("regress", 0) > 0.10:
        report.recommendations.append(
            "Regress rate >10% — tighten verifier gate before accepting steps."
        )
    if report.total_cache_read > report.total_tokens_in * 0.5:
        report.recommendations.append(
            "Cache reads dominate — audit repeated file reads across agent sessions."
        )

    return report


def analyze_file(path: Path) -> WastageReport:
    """Load a JSONL trace file and run ``analyze_wastage`` on it."""
    return analyze_wastage(_load_jsonl(path))
