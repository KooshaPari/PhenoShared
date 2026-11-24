"""Collect traces from 5+ harness log sources into unified JSONL.

v0.12 task 20: when dual-write is enabled (via ``TRACERA_DUAL_WRITE=1``
env var or ``runtime_config.trace_bridges.dual_write=True``), the
production path mirrors each event to the Tracera persistent trace
repository via ``TraceraBridge``. The bridge is constructed lazily
on first emit; construction failures are logged and the ingest
falls back to JSONL-only mode (fail-soft).
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pheno.paths import (
    AGENT_RUNNER_DIR,
    CURSOR_PROJECTS,
    FORGE_DIR,
    FORGE_DISPATCH_DIR,
    OMNIROUTE_DB,
    TRAINING_DIR,
)

if TYPE_CHECKING:
    from pheno.trace_store import TraceEvent as BridgeTraceEvent
    from traces.tracera_bridge import TraceraBridge


logger = logging.getLogger(__name__)


# Env var that forces dual-write ON regardless of config (handy for
# production rollouts where flipping a runtime config from outside
# the orchestrator is not always possible).
TRACERA_DUAL_WRITE_ENV = "TRACERA_DUAL_WRITE"
_TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})


@dataclass
class TraceEvent:
    """A single normalized harness trace event (union of 5+ sources)."""

    source: str
    event_type: str
    timestamp: str
    tokens_in: int = 0
    tokens_out: int = 0
    tokens_cache_read: int = 0
    duration_ms: int = 0
    model: str = ""
    provider: str = ""
    harness: str = ""
    session_id: str = ""
    motion_hint: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the event to a JSON-friendly dict."""
        return asdict(self)


ROLE_IDS = {
    "solo_engineer",
    "coding_subagent",
    "reviewer",
    "planner_manager",
    "planner_sponsor",
    "qa_test",
    "perf_profiler",
    "release_integration",
    "advisor_critic",
}


def infer_role(event: dict[str, Any]) -> str:
    """Infer a conservative role from explicit metadata, then prompt hints."""
    meta = event.get("meta") or {}
    explicit = event.get("role") or meta.get("role") or meta.get("role_id")
    if explicit in ROLE_IDS:
        return str(explicit)
    text = " ".join(
        str(event.get(key, "")) for key in ("prompt", "content", "request_summary")
    )
    lowered = text.lower()
    if any(term in lowered for term in ("review this diff", "code review", "reviewer")):
        return "reviewer"
    if any(
        term in lowered
        for term in ("write tests", "fix the test", "qa", "pytest", "test coverage")
    ):
        return "qa_test"
    if any(
        term in lowered
        for term in ("plan", "decompose", "assign subagent", "dag", "milestone")
    ):
        return "planner_manager"
    if any(
        term in lowered
        for term in ("profile", "latency", "throughput", "benchmark", "hot path")
    ):
        return "perf_profiler"
    if any(
        term in lowered for term in ("ship", "release", "changelog", "tag", "deploy")
    ):
        return "release_integration"
    if any(term in lowered for term in ("advise", "critic", "sponsor", "recommend")):
        return "advisor_critic"
    return "solo_engineer"


def trace_eligibility(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Check minimum evidence before a trace can enter human review."""
    turns = len(events)
    text = " ".join(json.dumps(event, ensure_ascii=False) for event in events).lower()
    recovery = any(
        term in text for term in ("retry", "recover", "escalat", "failed", "replan")
    )
    outcome = any(
        term in text
        for term in (
            "commit",
            "test",
            "passed",
            "failed",
            "ship",
            "complete",
            "verdict",
        )
    )
    eligible = turns >= 30 and recovery and outcome
    return {
        "eligible": eligible,
        "turns": turns,
        "has_recovery_or_escalation": recovery,
        "has_terminal_outcome": outcome,
        "reason": "ok" if eligible else "requires 30 turns, recovery, and outcome",
    }


class TraceCollector:
    """Incremental collectors per source."""

    def __init__(self, omniroute_db: Path | None = None):
        """Initialize the collector with an optional OmniRoute SQLite path."""
        self.omniroute_db = omniroute_db or OMNIROUTE_DB

    def omniroute(self, limit: int | None = None) -> Iterator[TraceEvent]:
        """Yield call_log rows from the OmniRoute SQLite DB as TraceEvents."""
        if not self.omniroute_db.exists():
            return
        conn = sqlite3.connect(self.omniroute_db)
        conn.row_factory = sqlite3.Row
        q = """
            SELECT id, timestamp, model, provider, combo_name, duration,
                   tokens_in, tokens_out, tokens_cache_read, tokens_compressed,
                   status, error_summary, request_summary
            FROM call_logs ORDER BY id DESC
        """
        if limit:
            q += f" LIMIT {int(limit)}"
        for row in conn.execute(q):
            yield TraceEvent(
                source="omniroute",
                event_type="llm_call",
                timestamp=row["timestamp"] or "",
                tokens_in=int(row["tokens_in"] or 0),
                tokens_out=int(row["tokens_out"] or 0),
                tokens_cache_read=int(row["tokens_cache_read"] or 0),
                duration_ms=int(row["duration"] or 0),
                model=row["model"] or "",
                provider=row["provider"] or "",
                harness="omniroute",
                session_id=str(row["id"]),
                meta={
                    "combo": row["combo_name"],
                    "status": row["status"],
                    "tokens_compressed": row["tokens_compressed"],
                    "error_summary": row["error_summary"],
                    "request_summary": (row["request_summary"] or "")[:500],
                },
            )
        conn.close()

    def forge(self) -> Iterator[TraceEvent]:
        """Yield trace events from the ``~/.forge/.forge_history`` file + credentials config."""
        history = FORGE_DIR / ".forge_history"
        if history.exists():
            for i, line in enumerate(
                history.read_text(encoding="utf-8", errors="replace").splitlines()
            ):
                if not line.strip():
                    continue
                yield TraceEvent(
                    source="forge",
                    event_type="history_line",
                    timestamp=datetime.now(UTC).isoformat(),
                    harness="forge",
                    session_id=f"forge_hist_{i}",
                    meta={"line": line[:2000]},
                )
        creds = FORGE_DIR / ".credentials.json"
        if creds.exists():
            yield TraceEvent(
                source="forge",
                event_type="config_snapshot",
                timestamp=datetime.now(UTC).isoformat(),
                harness="forge",
                session_id="forge_credentials",
                meta={"path": str(creds), "provider": "openai_compatible"},
            )

    def codex(self) -> Iterator[TraceEvent]:
        """Yield trace events from Codex sessions, agent_runner jobs, and forge_dispatch logs."""
        codex_sessions = Path.home() / ".codex" / "sessions"
        if codex_sessions.exists():
            for path in codex_sessions.glob("**/*.jsonl"):
                try:
                    stat = path.stat()
                except OSError:
                    continue
                yield TraceEvent(
                    source="codex",
                    event_type="session_log",
                    timestamp=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                    harness="codex",
                    session_id=path.stem,
                    meta={"path": str(path), "bytes": stat.st_size},
                )
        jobs_dir = AGENT_RUNNER_DIR / "jobs"
        if jobs_dir.exists():
            for path in sorted(jobs_dir.glob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                yield TraceEvent(
                    source="codex",
                    event_type="agent_job",
                    timestamp=data.get("finished_at") or data.get("started_at") or "",
                    model=data.get("model", "codex-spark"),
                    provider="openai",
                    harness="agent_runner",
                    session_id=data.get("id") or path.stem,
                    duration_ms=int(data.get("duration_ms") or 0),
                    meta={
                        "state": data.get("state"),
                        "thread_id": data.get("thread_id"),
                        "cwd": data.get("cwd"),
                        "prompt_len": len(data.get("prompt") or ""),
                    },
                )
        if FORGE_DISPATCH_DIR.exists():
            for log in FORGE_DISPATCH_DIR.glob("logs/*.log"):
                stat = log.stat()
                yield TraceEvent(
                    source="codex",
                    event_type="forge_dispatch_log",
                    timestamp=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                    harness="forge_dispatch",
                    session_id=log.stem,
                    meta={"path": str(log), "bytes": stat.st_size},
                )

    def claude_code(self) -> Iterator[TraceEvent]:
        """Yield trace events from ``~/.claude/**/transcript*.jsonl`` files."""
        claude_root = Path.home() / ".claude"
        for pattern in ("**/transcript*.jsonl", "**/sessions/**/*.jsonl", "**/*.jsonl"):
            for path in claude_root.glob(pattern):
                if "node_modules" in str(path):
                    continue
                try:
                    stat = path.stat()
                except OSError:
                    continue
                yield TraceEvent(
                    source="claude_code",
                    event_type="session_log",
                    timestamp=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                    harness="claude_code",
                    session_id=path.stem,
                    meta={"path": str(path), "bytes": stat.st_size},
                )

    def cursor_and_droid(self) -> Iterator[TraceEvent]:
        """Yield trace events from Cursor agent transcripts and Factory/Droid logs."""
        if CURSOR_PROJECTS.exists():
            for path in CURSOR_PROJECTS.glob("**/agent-transcripts/*.jsonl"):
                try:
                    stat = path.stat()
                except OSError:
                    continue
                yield TraceEvent(
                    source="cursor_agent",
                    event_type="agent_transcript",
                    timestamp=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                    harness="cursor_task",
                    session_id=path.stem,
                    meta={"path": str(path), "bytes": stat.st_size},
                )

    def public_analyses(
        self, downloads_root: Path | None = None
    ) -> Iterator[TraceEvent]:
        """Index public analysis documents as non-scoreable reference material."""
        root = downloads_root or Path("D:/koosh/Downloads")
        if not root.exists():
            return
        for path in sorted(root.glob("ChatGPT-*.md")):
            try:
                stat = path.stat()
            except OSError:
                continue
            yield TraceEvent(
                source="public_analysis",
                event_type="reference_document",
                timestamp=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                harness="reference_corpus",
                session_id=path.stem,
                meta={
                    "path": str(path),
                    "bytes": stat.st_size,
                    "scoreable": False,
                    "reason": "analysis reference, not an executable trace",
                },
            )
        for droid_root in (Path.home() / ".factory", Path.home() / ".droid"):
            if not droid_root.exists():
                continue
            for path in droid_root.rglob("*.jsonl"):
                try:
                    stat = path.stat()
                except OSError:
                    continue
                yield TraceEvent(
                    source="factory_droid",
                    event_type="droid_log",
                    timestamp=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                    harness="factory_droid",
                    session_id=path.stem,
                    meta={"path": str(path), "bytes": stat.st_size},
                )

    def all_sources(
        self, omniroute_limit: int | None = 5000, include_public_analysis: bool = False
    ) -> Iterator[TraceEvent]:
        """Yield every trace event from every registered source, in order."""
        yield from self.omniroute(limit=omniroute_limit)
        yield from self.forge()
        yield from self.codex()
        yield from self.claude_code()
        yield from self.cursor_and_droid()
        if include_public_analysis:
            yield from self.public_analyses()


def collect_all(
    out_dir: Path | None = None,
    omniroute_limit: int | None = 5000,
    include_public_analysis: bool = False,
) -> tuple[Path, int]:
    """Run all collectors and emit a unified JSONL file; returns ``(path, count)``.

    When ``TRACERA_DUAL_WRITE=1`` is set in the environment, or when
    ``runtime_config.trace_bridges.dual_write=True`` is set in
    ``config/pheno_runtime.yaml``, each event is also mirrored to the
    Tracera persistent trace repository via ``TraceraBridge``. The
    mirror is fail-soft: Tracera transport errors are logged and
    never propagate to the caller. When the bridge cannot be
    constructed (e.g. missing host/port), a warning is logged and
    the ingest falls back to JSONL-only mode.
    """
    out_dir = out_dir or TRAINING_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"traces_unified_{ts}.jsonl"
    collector = TraceCollector()

    # Wire the TraceraBridge if dual-write is enabled. ``_build_bridge``
    # returns None when dual-write is disabled OR when the
    # TraceraAdapter cannot be constructed (fail-soft).
    bridge = _build_dual_write_bridge(out_path)

    n = 0
    if bridge is not None:
        # Route every event through the bridge — it owns the JSONL
        # sink AND the Tracera mirror. The bridge's own
        # counter timestamps and ordering are preserved.
        for ev in collector.all_sources(
            omniroute_limit=omniroute_limit,
            include_public_analysis=include_public_analysis,
        ):
            bridge.emit(_to_bridge_event(ev))
            n += 1
    else:
        # Plain JSONL write (legacy behavior; matches pre-v0.12 output).
        with out_path.open("w", encoding="utf-8") as f:
            for ev in collector.all_sources(
                omniroute_limit=omniroute_limit,
                include_public_analysis=include_public_analysis,
            ):
                f.write(json.dumps(ev.to_dict(), ensure_ascii=False) + "\n")
                n += 1
    return out_path, n


# ---------------------------------------------------------------------------
# Tracera dual-write helpers (v0.12 task 20)
# ---------------------------------------------------------------------------


def _dual_write_enabled() -> bool:
    """Decide whether the Tracera dual-write bridge should be wired in.

    Returns True when **either** of the following is true:

    - ``TRACERA_DUAL_WRITE`` env var is set to a truthy value
      (case-insensitive ``1|true|yes|on``). This is the production
      rollout override — it forces dual-write ON regardless of the
      config file.
    - ``runtime_config.trace_bridges.dual_write`` is True in
      ``config/pheno_runtime.yaml``.

    Any exception raised while loading the runtime config is treated
    as "config not available" and falls back to "config said off";
    only the env var can force dual-write on in that case.
    """
    env = os.environ.get(TRACERA_DUAL_WRITE_ENV, "").strip().lower()
    if env in _TRUTHY_ENV_VALUES:
        return True
    try:
        from pheno.runtime_config import load_config
    except ImportError:
        return False
    try:
        cfg = load_config()
    except Exception as exc:  # noqa: BLE001 - defensive: fail-soft
        logger.warning(
            "traces.ingest: failed to load runtime config for dual-write "
            "check (%s); treating as disabled",
            exc,
        )
        return False
    return bool(cfg.trace_bridges.dual_write)


def _has_tracera_endpoint(cfg: Any) -> bool:
    """Verify the TraceraConfig block has a usable host + port.

    The runtime config defaults guarantee host/port are populated, but
    a user-supplied config might null them out. We treat that as
    "Tracera not configured" and fall back to JSONL-only mode.
    """
    host = getattr(cfg.tracera, "host", None)
    port = getattr(cfg.tracera, "port", None)
    if not host:
        return False
    try:
        port_int = int(port)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return port_int > 0


def _build_dual_write_bridge(jsonl_path: Path) -> TraceraBridge | None:
    """Build a TraceraBridge for the production ingest path.

    Returns ``None`` when:
    - dual-write is disabled (config + env var both off), OR
    - the Tracera config has no usable host/port, OR
    - the TraceraAdapter constructor raises for any reason.

    In all failure modes, a warning is logged so the operator can
    diagnose the misconfiguration. The caller then falls back to
    plain JSONL writes (the pre-v0.12 behavior).
    """
    if not _dual_write_enabled():
        return None
    try:
        from pheno.runtime_config import load_config
        from pheno.trace_store import TraceraAdapter
        from traces.tracera_bridge import TraceraBridge

        cfg = load_config()
    except Exception as exc:  # noqa: BLE001 - defensive: fail-soft
        logger.warning(
            "traces.ingest: dual-write enabled but config import failed "
            "(%s); falling back to JSONL only",
            exc,
        )
        return None

    if not _has_tracera_endpoint(cfg):
        logger.warning(
            "traces.ingest: dual-write enabled but TraceraConfig has no "
            "usable host/port (host=%r, port=%r); falling back to JSONL only",
            getattr(cfg.tracera, "host", None),
            getattr(cfg.tracera, "port", None),
        )
        return None

    try:
        adapter = TraceraAdapter(
            host=cfg.tracera.host,
            port=cfg.tracera.port,
            base_url=cfg.tracera.base_url,
            token=cfg.tracera.api_token,
            timeout=float(cfg.tracera.timeout_s),
        )
    except Exception as exc:  # noqa: BLE001 - defensive: fail-soft
        logger.warning(
            "traces.ingest: TraceraAdapter construction failed (%s); "
            "falling back to JSONL only",
            exc,
        )
        return None

    try:
        return TraceraBridge(
            adapter=adapter,
            jsonl_path=jsonl_path,
            config=cfg,
            dual_write=True,
            include_kinds=list(cfg.trace_bridges.include_kinds),
        )
    except Exception as exc:  # noqa: BLE001 - defensive: fail-soft
        logger.warning(
            "traces.ingest: TraceraBridge construction failed (%s); "
            "falling back to JSONL only",
            exc,
        )
        return None


def _to_bridge_event(ev: TraceEvent) -> BridgeTraceEvent:
    """Convert a ``traces.ingest.TraceEvent`` to a ``pheno.trace_store.TraceEvent``.

    Field mapping (matches the spec in
    ``docs/integrations/tracera-events.md``):

    - ``id``        → fresh UUID v4 (per-emit; trace_store has no
                      session-stable id concept in ``traces.ingest``)
    - ``kind``      → ``event_type`` (e.g. ``llm_call``,
                      ``history_line``, ``session_log``, ``agent_job``)
    - ``ts``        → ``timestamp`` (parsed from ISO 8601; falls back
                      to "now UTC" if the source string is empty /
                      malformed)
    - ``actor``     → ``source`` (omniroute | forge | codex |
                      claude_code | cursor_agent | public_analysis |
                      factory_droid)
    - ``target``    → ``harness`` (omniroute | forge | agent_runner |
                      forge_dispatch | claude_code | cursor_task |
                      reference_corpus | factory_droid | None)
    - ``session_id``→ ``session_id`` (copied as-is)
    - ``payload``   → all other fields (tokens_in, tokens_out,
                      tokens_cache_read, duration_ms, model, provider,
                      motion_hint, meta, source)
    """
    # Local imports keep the cold-start path lean.
    from uuid import uuid4

    from pheno.trace_store import TraceEvent as BridgeTraceEvent

    ts = _parse_iso8601(ev.timestamp) or datetime.now(UTC)
    # Build the payload from the harness-specific fields. Keys are
    # stable strings; the bridge will JSON-encode them via the
    # TraceraAdapter's append_event().
    payload: dict[str, Any] = {
        "source": ev.source,
        "tokens_in": ev.tokens_in,
        "tokens_out": ev.tokens_out,
        "tokens_cache_read": ev.tokens_cache_read,
        "duration_ms": ev.duration_ms,
        "model": ev.model,
        "provider": ev.provider,
        "motion_hint": ev.motion_hint,
        "meta": dict(ev.meta) if ev.meta else {},
    }
    return BridgeTraceEvent(
        id=uuid4(),
        kind=ev.event_type or "unknown",
        ts=ts,
        actor=ev.source or "unknown",
        target=ev.harness or None,
        session_id=ev.session_id or None,
        payload=payload,
    )


def _parse_iso8601(value: str) -> datetime | None:
    """Parse a (possibly-empty) ISO 8601 timestamp into a tz-aware datetime.

    Returns ``None`` for empty / malformed input. The trailing ``Z``
    suffix is normalized to ``+00:00`` so ``datetime.fromisoformat``
    accepts it on Python 3.11+.
    """
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
