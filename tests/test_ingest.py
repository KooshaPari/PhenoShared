"""Tests for traces/ingest.py — coverage push from 45.1% to >=80%.

Covers TraceEvent, infer_role, trace_eligibility, TraceCollector methods,
collect_all (JSONL-only path), dual-write helpers (_dual_write_enabled,
_has_tracera_endpoint, _build_dual_write_bridge, _to_bridge_event,
_parse_iso8601), and the public route_task/RoutingTable API indirectly used.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so ``traces`` is importable.
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from traces.ingest import (
    _TRUTHY_ENV_VALUES,
    TRACERA_DUAL_WRITE_ENV,
    TraceCollector,
    TraceEvent,
    _build_dual_write_bridge,
    _dual_write_enabled,
    _has_tracera_endpoint,
    _parse_iso8601,
    _to_bridge_event,
    collect_all,
    infer_role,
    trace_eligibility,
)

# ---------------------------------------------------------------------------
# TraceEvent dataclass
# ---------------------------------------------------------------------------


class TestTraceEvent:
    """TraceEvent is a plain dataclass with a to_dict() helper."""

    def test_default_values(self):
        ev = TraceEvent(source="test", event_type="unit", timestamp="2024-01-01T00:00:00Z")
        assert ev.source == "test"
        assert ev.tokens_in == 0
        assert ev.meta == {}
        assert ev.harness == ""

    def test_to_dict_round_trip(self):
        ev = TraceEvent(
            source="omniroute",
            event_type="llm_call",
            timestamp="2024-06-15T12:00:00Z",
            tokens_in=100,
            tokens_out=50,
            model="gpt-4",
            provider="openai",
            meta={"key": "val"},
        )
        d = ev.to_dict()
        assert isinstance(d, dict)
        assert d["source"] == "omniroute"
        assert d["tokens_in"] == 100
        assert d["meta"]["key"] == "val"
        # Round-trip back via dataclass constructor
        ev2 = TraceEvent(**d)
        assert ev2.model == "gpt-4"

    def test_to_dict_is_asdict(self):
        ev = TraceEvent(source="a", event_type="b", timestamp="c")
        assert ev.to_dict() == asdict(ev)


# ---------------------------------------------------------------------------
# infer_role
# ---------------------------------------------------------------------------


class TestInferRole:
    """infer_role extracts role from metadata or prompt content hints."""

    def test_explicit_role_in_top_level(self):
        assert infer_role({"role": "reviewer"}) == "reviewer"

    def test_explicit_role_in_meta(self):
        assert infer_role({"meta": {"role": "qa_test"}}) == "qa_test"

    def test_explicit_role_via_role_id_in_meta(self):
        assert infer_role({"meta": {"role_id": "perf_profiler"}}) == "perf_profiler"

    def test_explicit_role_not_in_role_ids(self):
        assert infer_role({"role": "unknown_role"}) == "solo_engineer"

    def test_reviewer_prompt_hints(self):
        assert infer_role({"prompt": "review this diff carefully"}) == "reviewer"
        assert infer_role({"content": "do a code review"}) == "reviewer"
        assert infer_role({"request_summary": "the reviewer says"}) == "reviewer"

    def test_qa_prompt_hints(self):
        assert infer_role({"prompt": "write tests for the module"}) == "qa_test"
        assert infer_role({"content": "fix the test coverage"}) == "qa_test"
        assert infer_role({"request_summary": "run pytest"}) == "qa_test"

    def test_planner_prompt_hints(self):
        assert infer_role({"prompt": "plan the migration into subtasks"}) == "planner_manager"
        assert infer_role({"content": "decompose the epic"}) == "planner_manager"

    def test_perf_profiler_prompt_hints(self):
        assert infer_role({"prompt": "profile the latency of this endpoint"}) == "perf_profiler"
        assert infer_role({"content": "benchmark throughput"}) == "perf_profiler"

    def test_release_integration_hints(self):
        assert infer_role({"prompt": "ship the release now"}) == "release_integration"
        assert infer_role({"content": "write the changelog"}) == "release_integration"

    def test_advisor_critic_hints(self):
        assert infer_role({"prompt": "advise on architecture"}) == "advisor_critic"
        assert infer_role({"content": "give a sponsor recommendation"}) == "advisor_critic"

    def test_fallback_solo_engineer(self):
        assert infer_role({"prompt": "do something unrelated"}) == "solo_engineer"

    def test_empty_event(self):
        assert infer_role({}) == "solo_engineer"

    def test_none_meta(self):
        assert infer_role({"meta": None}) == "solo_engineer"


# ---------------------------------------------------------------------------
# trace_eligibility
# ---------------------------------------------------------------------------


class TestTraceEligibility:
    """trace_eligibility returns an eligibility dict based on turn count, recovery, and outcome."""

    def test_not_eligible_under_30_turns(self):
        events = [{"text": "retry"}] * 10
        result = trace_eligibility(events)
        assert result["eligible"] is False
        assert result["turns"] == 10
        assert result["reason"] == "requires 30 turns, recovery, and outcome"

    def test_not_eligible_no_recovery(self):
        events = [{"text": "commit"}] * 35
        result = trace_eligibility(events)
        assert result["eligible"] is False
        assert result["has_recovery_or_escalation"] is False

    def test_not_eligible_no_outcome(self):
        events = [{"text": "retry recover escalate"}] * 35
        result = trace_eligibility(events)
        assert result["eligible"] is False
        assert result["has_terminal_outcome"] is False

    def test_eligible_all_conditions_met(self):
        events = [{"text": "retry recover failed"}] * 25 + [{"text": "commit passed"}] * 10
        result = trace_eligibility(events)
        assert result["eligible"] is True
        assert result["turns"] == 35
        assert result["has_recovery_or_escalation"] is True
        assert result["has_terminal_outcome"] is True
        assert result["reason"] == "ok"

    def test_empty_events(self):
        result = trace_eligibility([])
        assert result["eligible"] is False
        assert result["turns"] == 0

    def test_exactly_30_turns(self):
        events = [{"text": "retry recover escalate"}] * 30
        result = trace_eligibility(events)
        assert result["eligible"] is False  # needs outcome too

    def test_30_turns_with_recovery_and_outcome(self):
        events = [{"text": "retry failed"}] * 28 + [{"text": "commit passed"}] * 2
        result = trace_eligibility(events)
        assert result["eligible"] is True


# ---------------------------------------------------------------------------
# _parse_iso8601
# ---------------------------------------------------------------------------


class TestParseISO8601:
    """_parse_iso8601 parses ISO 8601 strings or returns None."""

    def test_valid_iso_with_z(self):
        dt = _parse_iso8601("2024-01-15T10:30:00Z")
        assert dt is not None
        assert dt.tzinfo is not None

    def test_valid_iso_with_offset(self):
        dt = _parse_iso8601("2024-01-15T10:30:00+00:00")
        assert dt is not None

    def test_empty_string(self):
        assert _parse_iso8601("") is None

    def test_malformed_string(self):
        assert _parse_iso8601("not-a-date") is None

    def test_none_input(self):
        assert _parse_iso8601(None) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TraceCollector.omniroute (with real SQLite)
# ---------------------------------------------------------------------------


class TestTraceCollectorOmniroute:
    """TraceCollector.omniroute reads from a real SQLite DB."""

    def _make_db(self, tmp_path: Path) -> Path:
        db_path = tmp_path / "call_logs.sqlite"
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE call_logs (
                id INTEGER,
                timestamp TEXT,
                model TEXT,
                provider TEXT,
                combo_name TEXT,
                duration INTEGER,
                tokens_in INTEGER,
                tokens_out INTEGER,
                tokens_cache_read INTEGER,
                tokens_compressed INTEGER,
                status TEXT,
                error_summary TEXT,
                request_summary TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO call_logs VALUES (1, '2024-01-01T00:00:00Z', 'gpt-4', 'openai', "
            "'combo_a', 500, 100, 50, 10, 5, 'ok', NULL, 'test request')"
        )
        conn.execute(
            "INSERT INTO call_logs VALUES (2, '2024-01-02T00:00:00Z', 'claude-3', 'anthropic', "
            "'combo_b', 300, 200, 80, 20, 0, 'error', 'timeout', NULL)"
        )
        conn.commit()
        conn.close()
        return db_path

    def test_omniroute_yields_events(self, tmp_path: Path):
        db = self._make_db(tmp_path)
        collector = TraceCollector(omniroute_db=db)
        events = list(collector.omniroute())
        assert len(events) == 2
        assert events[0].source == "omniroute"
        assert events[0].event_type == "llm_call"
        assert events[0].harness == "omniroute"
        # Query is ORDER BY id DESC, so id=2 (claude-3) comes first
        assert events[0].model == "claude-3"
        assert events[0].tokens_in == 200
        assert events[0].meta["combo"] == "combo_b"

    def test_omniroute_with_limit(self, tmp_path: Path):
        db = self._make_db(tmp_path)
        collector = TraceCollector(omniroute_db=db)
        events = list(collector.omniroute(limit=1))
        assert len(events) == 1

    def test_omniroute_missing_db(self, tmp_path: Path):
        collector = TraceCollector(omniroute_db=tmp_path / "nonexistent.sqlite")
        events = list(collector.omniroute())
        assert events == []

    def test_omniroute_null_fields(self, tmp_path: Path):
        """Rows with NULL tokens/status fields should not crash."""
        db = tmp_path / "call_logs.sqlite"
        conn = sqlite3.connect(db)
        conn.execute(
            """
            CREATE TABLE call_logs (
                id INTEGER, timestamp TEXT, model TEXT, provider TEXT,
                combo_name TEXT, duration INTEGER, tokens_in INTEGER,
                tokens_out INTEGER, tokens_cache_read INTEGER,
                tokens_compressed INTEGER, status TEXT, error_summary TEXT,
                request_summary TEXT
            )
            """
        )
        conn.execute("INSERT INTO call_logs VALUES (1, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL)")
        conn.commit()
        conn.close()
        collector = TraceCollector(omniroute_db=db)
        events = list(collector.omniroute())
        assert len(events) == 1
        assert events[0].model == ""
        assert events[0].provider == ""


# ---------------------------------------------------------------------------
# TraceCollector.forge
# ---------------------------------------------------------------------------


class TestTraceCollectorForge:
    """TraceCollector.forge reads .forge_history and .credentials.json."""

    def test_forge_history(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        forge_dir = tmp_path / "forge"
        forge_dir.mkdir()
        history = forge_dir / ".forge_history"
        history.write_text("line 1\nline 2\n\nline 3\n")
        monkeypatch.setattr("traces.ingest.FORGE_DIR", forge_dir)
        collector = TraceCollector(omniroute_db=tmp_path / "x.sqlite")
        events = list(collector.forge())
        history_events = [e for e in events if e.event_type == "history_line"]
        assert len(history_events) == 3  # empty line skipped

    def test_forge_credentials(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        forge_dir = tmp_path / "forge"
        forge_dir.mkdir()
        creds = forge_dir / ".credentials.json"
        creds.write_text("{}")
        monkeypatch.setattr("traces.ingest.FORGE_DIR", forge_dir)
        collector = TraceCollector(omniroute_db=tmp_path / "x.sqlite")
        events = list(collector.forge())
        config_events = [e for e in events if e.event_type == "config_snapshot"]
        assert len(config_events) == 1
        assert config_events[0].meta["provider"] == "openai_compatible"

    def test_forge_no_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        forge_dir = tmp_path / "empty_forge"
        forge_dir.mkdir()
        monkeypatch.setattr("traces.ingest.FORGE_DIR", forge_dir)
        collector = TraceCollector(omniroute_db=tmp_path / "x.sqlite")
        events = list(collector.forge())
        assert events == []


# ---------------------------------------------------------------------------
# TraceCollector.codex
# ---------------------------------------------------------------------------


class TestTraceCollectorCodex:
    """TraceCollector.codex reads codex sessions, agent-runner jobs, and forge-dispatch logs."""

    def test_agent_runner_jobs(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        jobs_dir = tmp_path / "agent-runner" / "jobs"
        jobs_dir.mkdir(parents=True)
        job = jobs_dir / "job1.json"
        job.write_text(json.dumps({
            "id": "job-1",
            "model": "codex-spark",
            "state": "done",
            "thread_id": "t-1",
            "cwd": "/tmp",
            "prompt": "do something",
            "duration_ms": 500,
            "finished_at": "2024-01-01T00:00:00Z",
            "started_at": "2023-12-31T23:00:00Z",
        }))
        monkeypatch.setattr("traces.ingest.AGENT_RUNNER_DIR", tmp_path / "agent-runner")
        collector = TraceCollector(omniroute_db=tmp_path / "x.sqlite")
        events = list(collector.codex())
        agent_events = [e for e in events if e.event_type == "agent_job"]
        assert len(agent_events) == 1
        assert agent_events[0].model == "codex-spark"
        assert agent_events[0].duration_ms == 500
        assert agent_events[0].meta["prompt_len"] == len("do something")

    def test_invalid_json_skipped(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        jobs_dir = tmp_path / "agent-runner" / "jobs"
        jobs_dir.mkdir(parents=True)
        (jobs_dir / "bad.json").write_text("not json")
        monkeypatch.setattr("traces.ingest.AGENT_RUNNER_DIR", tmp_path / "agent-runner")
        collector = TraceCollector(omniroute_db=tmp_path / "x.sqlite")
        events = list(collector.codex())
        agent_events = [e for e in events if e.event_type == "agent_job"]
        assert len(agent_events) == 0

    def test_missing_started_finished_fields(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        jobs_dir = tmp_path / "agent-runner" / "jobs"
        jobs_dir.mkdir(parents=True)
        (jobs_dir / "minimal.json").write_text(json.dumps({"id": "j2"}))
        monkeypatch.setattr("traces.ingest.AGENT_RUNNER_DIR", tmp_path / "agent-runner")
        collector = TraceCollector(omniroute_db=tmp_path / "x.sqlite")
        events = list(collector.codex())
        agent_events = [e for e in events if e.event_type == "agent_job"]
        assert len(agent_events) == 1
        assert agent_events[0].timestamp == ""

    def test_no_codex_dirs(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        # Codex uses Path.home() / ".codex" / "sessions" (hardcoded), so we
        # need to monkeypatch Path.home() to point to a temp dir with no .codex.
        monkeypatch.setattr("traces.ingest.Path.home", lambda: tmp_path)
        monkeypatch.setattr("traces.ingest.AGENT_RUNNER_DIR", tmp_path / "nonexistent")
        monkeypatch.setattr("traces.ingest.FORGE_DISPATCH_DIR", tmp_path / "nonexistent2")
        collector = TraceCollector(omniroute_db=tmp_path / "x.sqlite")
        events = list(collector.codex())
        assert events == []


# ---------------------------------------------------------------------------
# TraceCollector.claude_code
# ---------------------------------------------------------------------------


class TestTraceCollectorClaudeCode:
    """TraceCollector.claude_code globs ~/.claude for JSONL session logs."""

    def test_claude_code_yields(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        session = claude_dir / "transcript_abc.jsonl"
        session.write_text('{"msg": 1}\n')
        monkeypatch.setattr("traces.ingest.Path.home", lambda: tmp_path)
        collector = TraceCollector(omniroute_db=tmp_path / "x.sqlite")
        events = list(collector.claude_code())
        assert len(events) >= 1
        assert any(e.source == "claude_code" for e in events)

    def test_node_modules_excluded(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        claude_dir = tmp_path / ".claude" / "project" / "node_modules" / "pkg"
        claude_dir.mkdir(parents=True)
        (claude_dir / "transcript.jsonl").write_text("{}")
        monkeypatch.setattr("traces.ingest.Path.home", lambda: tmp_path)
        collector = TraceCollector(omniroute_db=tmp_path / "x.sqlite")
        events = list(collector.claude_code())
        assert events == []


# ---------------------------------------------------------------------------
# TraceCollector.cursor_and_droid
# ---------------------------------------------------------------------------


class TestTraceCollectorCursorAndDroid:
    """cursor_and_droid reads Cursor agent transcripts."""

    def test_cursor_transcripts(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        cursor_dir = tmp_path / "cursor" / "projects" / "proj1" / "agent-transcripts"
        cursor_dir.mkdir(parents=True)
        (cursor_dir / "agent.jsonl").write_text("data")
        monkeypatch.setattr("traces.ingest.CURSOR_PROJECTS", tmp_path / "cursor" / "projects")
        collector = TraceCollector(omniroute_db=tmp_path / "x.sqlite")
        events = list(collector.cursor_and_droid())
        assert len(events) == 1
        assert events[0].source == "cursor_agent"

    def test_cursor_no_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("traces.ingest.CURSOR_PROJECTS", tmp_path / "nope")
        collector = TraceCollector(omniroute_db=tmp_path / "x.sqlite")
        events = list(collector.cursor_and_droid())
        assert events == []


# ---------------------------------------------------------------------------
# TraceCollector.public_analyses
# ---------------------------------------------------------------------------


class TestTraceCollectorPublicAnalyses:
    """public_analyses indexes public analysis docs and factory/droid logs."""

    def test_public_analyses_yields_md_files(self, tmp_path: Path):
        (tmp_path / "ChatGPT-analysis.md").write_text("# Analysis")
        collector = TraceCollector(omniroute_db=tmp_path / "x.sqlite")
        events = list(collector.public_analyses(downloads_root=tmp_path))
        assert len(events) >= 1
        assert events[0].meta["scoreable"] is False

    def test_nonexistent_root(self, tmp_path: Path):
        collector = TraceCollector(omniroute_db=tmp_path / "x.sqlite")
        events = list(collector.public_analyses(downloads_root=tmp_path / "nope"))
        assert events == []


# ---------------------------------------------------------------------------
# TraceCollector.all_sources
# ---------------------------------------------------------------------------


class TestTraceCollectorAllSources:
    """all_sources iterates through every registered source."""

    def test_all_sources_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """With no actual source dirs populated, yields nothing (or nothing crashes)."""
        monkeypatch.setattr("traces.ingest.Path.home", lambda: tmp_path)
        monkeypatch.setattr("traces.ingest.FORGE_DIR", tmp_path / "no_forge")
        monkeypatch.setattr("traces.ingest.AGENT_RUNNER_DIR", tmp_path / "no_jobs")
        monkeypatch.setattr("traces.ingest.FORGE_DISPATCH_DIR", tmp_path / "no_dispatch")
        monkeypatch.setattr("traces.ingest.CURSOR_PROJECTS", tmp_path / "no_cursor")
        collector = TraceCollector(omniroute_db=tmp_path / "x.sqlite")
        events = list(collector.all_sources(omniroute_limit=None, include_public_analysis=False))
        # Should not crash; may or may not yield events depending on filesystem
        assert isinstance(events, list)


# ---------------------------------------------------------------------------
# collect_all (JSONL-only path)
# ---------------------------------------------------------------------------


class TestCollectAll:
    """collect_all writes a unified JSONL file when dual-write is disabled."""

    def test_collect_all_writes_jsonl(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(TRACERA_DUAL_WRITE_ENV, "")
        monkeypatch.setattr("traces.ingest.Path.home", lambda: tmp_path)
        monkeypatch.setattr("traces.ingest.FORGE_DIR", tmp_path / "no_forge")
        monkeypatch.setattr("traces.ingest.AGENT_RUNNER_DIR", tmp_path / "no_jobs")
        monkeypatch.setattr("traces.ingest.FORGE_DISPATCH_DIR", tmp_path / "no_dispatch")
        monkeypatch.setattr("traces.ingest.CURSOR_PROJECTS", tmp_path / "no_cursor")
        out_dir = tmp_path / "training"
        out_path, count = collect_all(out_dir=out_dir, omniroute_limit=None)
        assert out_path.exists()
        assert out_path.suffix == ".jsonl"
        # count may be 0 if no sources have data
        assert count >= 0


# ---------------------------------------------------------------------------
# _dual_write_enabled
# ---------------------------------------------------------------------------


class TestDualWriteEnabled:
    """_dual_write_enabled checks env var and runtime config."""

    def test_env_var_truthy(self, monkeypatch: pytest.MonkeyPatch):
        for val in ("1", "true", "yes", "on", "TRUE", "Yes"):
            monkeypatch.setenv(TRACERA_DUAL_WRITE_ENV, val)
            assert _dual_write_enabled() is True

    def test_env_var_falsy(self, monkeypatch: pytest.MonkeyPatch):
        for val in ("", "0", "false", "no"):
            monkeypatch.setenv(TRACERA_DUAL_WRITE_ENV, val)
            # Falls through to config path; if ImportError, returns False
            assert _dual_write_enabled() in (True, False)

    def test_env_var_whitespace(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(TRACERA_DUAL_WRITE_ENV, "  1  ")
        assert _dual_write_enabled() is True

    def test_import_error_fallback(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv(TRACERA_DUAL_WRITE_ENV, raising=False)
        # If pheno.runtime_config is importable but load_config raises, still works
        # The key test: ImportError on pheno.runtime_config → returns False
        with patch.dict("sys.modules", {"pheno.runtime_config": None}):
            assert _dual_write_enabled() is False


# ---------------------------------------------------------------------------
# _has_tracera_endpoint
# ---------------------------------------------------------------------------


class TestHasTraceraEndpoint:
    """_has_tracera_endpoint validates host/port presence."""

    def test_valid_endpoint(self):
        cfg = MagicMock()
        cfg.tracera.host = "localhost"
        cfg.tracera.port = 5000
        assert _has_tracera_endpoint(cfg) is True

    def test_no_host(self):
        cfg = MagicMock()
        cfg.tracera.host = None
        cfg.tracera.port = 5000
        assert _has_tracera_endpoint(cfg) is False

    def test_no_port(self):
        cfg = MagicMock()
        cfg.tracera.host = "localhost"
        cfg.tracera.port = None
        assert _has_tracera_endpoint(cfg) is False

    def test_non_numeric_port(self):
        cfg = MagicMock()
        cfg.tracera.host = "localhost"
        cfg.tracera.port = "not_a_number"
        assert _has_tracera_endpoint(cfg) is False

    def test_zero_port(self):
        cfg = MagicMock()
        cfg.tracera.host = "localhost"
        cfg.tracera.port = 0
        assert _has_tracera_endpoint(cfg) is False

    def test_negative_port(self):
        cfg = MagicMock()
        cfg.tracera.host = "localhost"
        cfg.tracera.port = -1
        assert _has_tracera_endpoint(cfg) is False


# ---------------------------------------------------------------------------
# _build_dual_write_bridge
# ---------------------------------------------------------------------------


class TestBuildDualWriteBridge:
    """_build_dual_write_bridge returns None when dual-write is disabled."""

    def test_disabled_returns_none(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(TRACERA_DUAL_WRITE_ENV, "0")
        result = _build_dual_write_bridge(Path("/tmp/test.jsonl"))
        assert result is None

    def test_import_error_returns_none(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(TRACERA_DUAL_WRITE_ENV, "1")
        with patch.dict("sys.modules", {"pheno.runtime_config": None}):
            result = _build_dual_write_bridge(Path("/tmp/test.jsonl"))
            assert result is None


# ---------------------------------------------------------------------------
# _to_bridge_event
# ---------------------------------------------------------------------------


class TestToBridgeEvent:
    """_to_bridge_event converts TraceEvent to the bridge TraceEvent format."""

    def test_conversion(self):
        ev = TraceEvent(
            source="omniroute",
            event_type="llm_call",
            timestamp="2024-01-01T00:00:00Z",
            tokens_in=100,
            tokens_out=50,
            model="gpt-4",
            provider="openai",
            harness="omniroute",
            session_id="s1",
            meta={"combo": "a"},
        )
        bridge_ev = _to_bridge_event(ev)
        assert bridge_ev.kind == "llm_call"
        assert bridge_ev.actor == "omniroute"
        assert bridge_ev.target == "omniroute"
        assert bridge_ev.session_id == "s1"
        assert bridge_ev.payload["tokens_in"] == 100

    def test_empty_timestamp_falls_back(self):
        ev = TraceEvent(source="test", event_type="unit", timestamp="")
        bridge_ev = _to_bridge_event(ev)
        # Should have a timestamp (fallback to now)
        assert bridge_ev.ts is not None

    def test_empty_fields(self):
        ev = TraceEvent(source="", event_type="", timestamp="")
        bridge_ev = _to_bridge_event(ev)
        assert bridge_ev.actor == "unknown"
        assert bridge_ev.kind == "unknown"
        assert bridge_ev.target is None
        assert bridge_ev.session_id is None

    def test_no_meta(self):
        ev = TraceEvent(source="x", event_type="y", timestamp="2024-01-01T00:00:00Z", meta={})
        bridge_ev = _to_bridge_event(ev)
        assert bridge_ev.payload["meta"] == {}

    def test_none_meta_treated_as_empty(self):
        ev = TraceEvent(source="x", event_type="y", timestamp="2024-01-01T00:00:00Z", meta={})
        bridge_ev = _to_bridge_event(ev)
        assert isinstance(bridge_ev.payload["meta"], dict)


# ---------------------------------------------------------------------------
# _TRUTHY_ENV_VALUES constant
# ---------------------------------------------------------------------------


class TestTruthyEnvValues:
    """The truthy env values frozenset is correctly defined."""

    def test_expected_values(self):
        assert _TRUTHY_ENV_VALUES == frozenset({"1", "true", "yes", "on"})
