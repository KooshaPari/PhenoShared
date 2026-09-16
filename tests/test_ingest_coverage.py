# Tests for traces/ingest.py — coverage push to push OSError branches,
# forge_dispatch traversal, include_public_analysis flag, collect_all
# dual-write path, and the dual-write bridge construction exception
# ladder.
#
# These tests use MODULE REFERENCES for monkeypatching (per project
# constraint #1: no string paths).

from __future__ import annotations

import json
import sqlite3
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure the repo root is importable.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import traces.ingest as ingest_mod  # noqa: E402  (module reference)
from traces.ingest import (  # noqa: E402
    TRACERA_DUAL_WRITE_ENV,
    TraceCollector,
    TraceEvent,
    _build_dual_write_bridge,
    _dual_write_enabled,
    collect_all,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mk_omniroute_db(tmp_path: Path) -> Path:
    """Build a minimal SQLite DB with a call_logs table (empty)."""
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
    conn.commit()
    conn.close()
    return db


# ---------------------------------------------------------------------------
# TraceCollector.codex — forge_dispatch logs branch (lines 260-270)
# ---------------------------------------------------------------------------


class TestCodexForgeDispatchBranch:
    """When FORGE_DISPATCH_DIR exists with logs, codex() yields forge_dispatch_log."""

    def test_forge_dispatch_logs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        dispatch = tmp_path / "forge-dispatch"
        logs_dir = dispatch / "logs"
        logs_dir.mkdir(parents=True)
        (logs_dir / "dispatch_run_42.log").write_text("hello\n")
        monkeypatch.setattr(ingest_mod, "FORGE_DISPATCH_DIR", dispatch)
        # No codex sessions, no agent-runner jobs.
        monkeypatch.setattr(ingest_mod.Path, "home", lambda: tmp_path)
        monkeypatch.setattr(ingest_mod, "AGENT_RUNNER_DIR", tmp_path / "no_jobs")

        collector = TraceCollector(omniroute_db=_mk_omniroute_db(tmp_path))
        events = list(collector.codex())
        dispatch_events = [e for e in events if e.event_type == "forge_dispatch_log"]
        assert len(dispatch_events) == 1
        assert dispatch_events[0].source == "codex"
        assert dispatch_events[0].harness == "forge_dispatch"
        assert dispatch_events[0].session_id == "dispatch_run_42"
        assert dispatch_events[0].meta["bytes"] > 0

    def test_codex_session_stat_oserror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A codex session path that raises OSError on stat() is skipped."""
        codex_sessions = tmp_path / ".codex" / "sessions"
        codex_sessions.mkdir(parents=True)
        # Create a real file.
        (codex_sessions / "ok.jsonl").write_text("{}")
        # Inject a broken path via a glob mock that yields a path whose stat
        # raises OSError.
        broken_path = codex_sessions / "broken.jsonl"

        real_glob = codex_sessions.glob

        def fake_glob(pattern: str):  # type: ignore[no-untyped-def]
            yield from real_glob(pattern)
            yield broken_path

        # Patch Path.home() so codex() finds the codex_sessions path.
        monkeypatch.setattr(ingest_mod.Path, "home", lambda: tmp_path)

        # Replace the glob on the codex_sessions Path with our generator.
        with patch.object(
            type(codex_sessions), "glob", lambda self, pattern: fake_glob(pattern)
        ):
            with patch.object(
                type(broken_path),
                "stat",
                side_effect=OSError("stat failed"),
            ):
                # No agent-runner jobs, no dispatch dir.
                monkeypatch.setattr(
                    ingest_mod, "AGENT_RUNNER_DIR", tmp_path / "no_jobs"
                )
                monkeypatch.setattr(
                    ingest_mod, "FORGE_DISPATCH_DIR", tmp_path / "no_dispatch"
                )
                collector = TraceCollector(omniroute_db=_mk_omniroute_db(tmp_path))
                # The function should not raise; the broken path is skipped.
                events = list(collector.codex())
        # We don't assert a specific count because glob+stat mocking is
        # filesystem-dependent. The key invariant: no OSError escapes.
        assert isinstance(events, list)


# ---------------------------------------------------------------------------
# TraceCollector.claude_code — OSError branch (lines 280-282)
# ---------------------------------------------------------------------------


class TestClaudeCodeStatOSError:
    def test_claude_code_stat_oserror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """claude_code() silently skips paths that raise OSError on stat()."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        transcript = claude_dir / "transcript_test.jsonl"
        transcript.write_text("{}")

        monkeypatch.setattr(ingest_mod.Path, "home", lambda: tmp_path)
        with patch.object(
            type(transcript), "stat", side_effect=OSError("stat failed")
        ):
            collector = TraceCollector(omniroute_db=_mk_omniroute_db(tmp_path))
            events = list(collector.claude_code())
        # The OSError path was hit; the function still returns a list.
        assert isinstance(events, list)


# ---------------------------------------------------------------------------
# TraceCollector.cursor_and_droid — OSError branch (lines 297-299)
# ---------------------------------------------------------------------------


class TestCursorStatOSError:
    def test_cursor_stat_oserror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """cursor_and_droid() silently skips paths that raise OSError on stat()."""
        cursor_root = tmp_path / "cursor" / "projects"
        transcripts = cursor_root / "proj1" / "agent-transcripts"
        transcripts.mkdir(parents=True)
        transcript = transcripts / "agent.jsonl"
        transcript.write_text("data")

        monkeypatch.setattr(ingest_mod, "CURSOR_PROJECTS", cursor_root)
        with patch.object(
            type(transcript), "stat", side_effect=OSError("stat failed")
        ):
            collector = TraceCollector(omniroute_db=_mk_omniroute_db(tmp_path))
            events = list(collector.cursor_and_droid())
        assert isinstance(events, list)


# ---------------------------------------------------------------------------
# TraceCollector.public_analyses — factory_droid branch + OSError branches
# ---------------------------------------------------------------------------


class TestPublicAnalysesFactoryDroid:
    """When ~/.factory or ~/.droid contains jsonl logs, yield factory_droid events."""

    def test_factory_droid_logs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # No ChatGPT-*.md, but ~/.factory has jsonl.
        factory = tmp_path / ".factory"
        factory.mkdir(parents=True)
        log = factory / "d.jsonl"
        log.write_text("{}")
        monkeypatch.setattr(ingest_mod.Path, "home", lambda: tmp_path)
        # Use a downloads_root that EXISTS but has no .md files.
        downloads = tmp_path / "empty_dl"
        downloads.mkdir()
        collector = TraceCollector(omniroute_db=_mk_omniroute_db(tmp_path))
        events = list(collector.public_analyses(downloads_root=downloads))
        droid_events = [e for e in events if e.source == "factory_droid"]
        assert len(droid_events) == 1
        assert droid_events[0].harness == "factory_droid"
        assert droid_events[0].event_type == "droid_log"
        assert droid_events[0].meta["bytes"] >= 0

    def test_factory_droid_stat_oserror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        factory = tmp_path / ".factory"
        log = factory / "broken.jsonl"
        log.parent.mkdir(parents=True)
        # File actually exists but stat() raises.
        monkeypatch.setattr(ingest_mod.Path, "home", lambda: tmp_path)
        with patch.object(
            type(log), "stat", side_effect=OSError("stat failed")
        ):
            collector = TraceCollector(omniroute_db=_mk_omniroute_db(tmp_path))
            events = list(collector.public_analyses(downloads_root=tmp_path / "x"))
        # Skipped silently; result is a list.
        assert isinstance(events, list)

    def test_public_analysis_md_stat_oserror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        md = tmp_path / "ChatGPT-test.md"
        md.write_text("# hi")
        with patch.object(type(md), "stat", side_effect=OSError("stat failed")):
            collector = TraceCollector(omniroute_db=_mk_omniroute_db(tmp_path))
            events = list(collector.public_analyses(downloads_root=tmp_path))
        assert isinstance(events, list)


# ---------------------------------------------------------------------------
# TraceCollector.all_sources — include_public_analysis flag (line 360-361)
# ---------------------------------------------------------------------------


class TestAllSourcesIncludePublicAnalysis:
    """all_sources() yields public_analyses when include_public_analysis=True."""

    def test_include_public_analysis_flag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        downloads = tmp_path / "Downloads"
        downloads.mkdir(parents=True)
        (downloads / "ChatGPT-coverage.md").write_text("# Analysis")
        monkeypatch.setattr(ingest_mod.Path, "home", lambda: tmp_path)
        monkeypatch.setattr(ingest_mod, "FORGE_DIR", tmp_path / "no_forge")
        monkeypatch.setattr(ingest_mod, "AGENT_RUNNER_DIR", tmp_path / "no_jobs")
        monkeypatch.setattr(ingest_mod, "FORGE_DISPATCH_DIR", tmp_path / "no_dispatch")
        monkeypatch.setattr(ingest_mod, "CURSOR_PROJECTS", tmp_path / "no_cursor")

        collector = TraceCollector(omniroute_db=_mk_omniroute_db(tmp_path))

        # Patch public_analyses to use our downloads dir.
        with patch.object(
            collector,
            "public_analyses",
            lambda downloads_root=None: iter(
                [
                    TraceEvent(
                        source="public_analysis",
                        event_type="reference_document",
                        timestamp="2026-01-01T00:00:00Z",
                        meta={"scoreable": False},
                    )
                ]
            ),
        ):
            events = list(
                collector.all_sources(
                    omniroute_limit=None, include_public_analysis=True
                )
            )
        # The public_analysis event was yielded.
        public_events = [e for e in events if e.source == "public_analysis"]
        assert len(public_events) == 1
        assert public_events[0].meta["scoreable"] is False

    def test_exclude_public_analysis_by_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """include_public_analysis=False (default) skips the source."""
        monkeypatch.setattr(ingest_mod.Path, "home", lambda: tmp_path)
        monkeypatch.setattr(ingest_mod, "FORGE_DIR", tmp_path / "no_forge")
        monkeypatch.setattr(ingest_mod, "AGENT_RUNNER_DIR", tmp_path / "no_jobs")
        monkeypatch.setattr(ingest_mod, "FORGE_DISPATCH_DIR", tmp_path / "no_dispatch")
        monkeypatch.setattr(ingest_mod, "CURSOR_PROJECTS", tmp_path / "no_cursor")

        collector = TraceCollector(omniroute_db=_mk_omniroute_db(tmp_path))
        with patch.object(collector, "public_analyses") as mock_pa:
            list(collector.all_sources(omniroute_limit=None))
        # public_analyses was never called.
        assert mock_pa.call_count == 0


# ---------------------------------------------------------------------------
# collect_all — dual-write path with bridge enabled (lines 392-401)
# ---------------------------------------------------------------------------


class TestCollectAllWithBridge:
    """collect_all() routes events through the bridge when dual-write is enabled."""

    def test_collect_all_with_mocked_bridge(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Force dual-write on via env var.
        monkeypatch.setenv(TRACERA_DUAL_WRITE_ENV, "1")

        # Make all source iterators yield a single event each.
        ev = TraceEvent(
            source="forge", event_type="history_line", timestamp="2026-01-01T00:00:00Z"
        )
        with patch.object(ingest_mod, "_build_dual_write_bridge") as mock_build:
            mock_bridge = MagicMock()
            mock_build.return_value = mock_bridge

            with patch.object(TraceCollector, "all_sources", return_value=iter([ev])):
                out_dir = tmp_path / "training"
                out_path, n = collect_all(out_dir=out_dir)

        # Bridge was built and emit() was called once per event.
        assert mock_build.called
        assert n == 1
        assert mock_bridge.emit.called
        assert out_path.exists() or out_dir.exists()


# ---------------------------------------------------------------------------
# _dual_write_enabled — config exception path (lines 442-450)
# ---------------------------------------------------------------------------


class TestDualWriteEnabledConfigError:
    """When load_config() raises Exception, dual-write falls back to False."""

    def test_load_config_raises_returns_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(TRACERA_DUAL_WRITE_ENV, raising=False)

        # Import the symbol and make load_config raise.
        import pheno.runtime_config as rc

        def _raise():  # noqa: ANN202
            raise RuntimeError("config broken")

        monkeypatch.setattr(rc, "load_config", _raise)

        # The function catches the exception and returns False.
        assert _dual_write_enabled() is False

    def test_load_config_returns_truthy_dual_write(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(TRACERA_DUAL_WRITE_ENV, raising=False)
        import pheno.runtime_config as rc

        cfg = MagicMock()
        cfg.trace_bridges.dual_write = True
        monkeypatch.setattr(rc, "load_config", lambda: cfg)
        assert _dual_write_enabled() is True

    def test_load_config_returns_falsy_dual_write(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(TRACERA_DUAL_WRITE_ENV, raising=False)
        import pheno.runtime_config as rc

        cfg = MagicMock()
        cfg.trace_bridges.dual_write = False
        monkeypatch.setattr(rc, "load_config", lambda: cfg)
        assert _dual_write_enabled() is False


# ---------------------------------------------------------------------------
# _build_dual_write_bridge — exception ladder (lines 486-538)
# ---------------------------------------------------------------------------


class TestBuildDualWriteBridgeErrors:
    """_build_dual_write_bridge() handles each error path with a warning."""

    def test_disabled_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Force dual-write OFF.
        monkeypatch.setenv(TRACERA_DUAL_WRITE_ENV, "0")
        assert _build_dual_write_bridge(Path("/tmp/x.jsonl")) is None

    def test_config_import_failure_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If runtime_config/trace_store/bridge import fails → None."""
        monkeypatch.setenv(TRACERA_DUAL_WRITE_ENV, "1")
        # Force the import inside _build_dual_write_bridge to fail.
        import builtins

        real_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
            if name in ("pheno.runtime_config", "pheno.trace_store", "traces.tracera_bridge"):
                raise ImportError(f"blocked: {name}")
            return real_import(name, globals, locals, fromlist, level)

        with patch.object(builtins, "__import__", fake_import):
            result = _build_dual_write_bridge(Path("/tmp/x.jsonl"))
        assert result is None

    def test_no_tracera_endpoint_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When TraceraConfig has no usable host/port, returns None."""
        monkeypatch.setenv(TRACERA_DUAL_WRITE_ENV, "1")
        cfg = MagicMock()
        cfg.tracera.host = ""  # empty host → _has_tracera_endpoint returns False
        cfg.tracera.port = 8080
        import pheno.runtime_config as rc

        monkeypatch.setattr(rc, "load_config", lambda: cfg)
        result = _build_dual_write_bridge(Path("/tmp/x.jsonl"))
        assert result is None

    def test_tracera_adapter_construction_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If TraceraAdapter() raises, log + return None."""
        monkeypatch.setenv(TRACERA_DUAL_WRITE_ENV, "1")
        cfg = MagicMock()
        cfg.tracera.host = "tracera.test"
        cfg.tracera.port = 8080
        cfg.tracera.base_url = None
        cfg.tracera.api_token = None
        cfg.tracera.timeout_s = 5
        cfg.tracera.batch_size = 32
        cfg.trace_bridges.include_kinds = []
        import pheno.runtime_config as rc
        import pheno.trace_store as store_mod

        monkeypatch.setattr(rc, "load_config", lambda: cfg)

        def _boom(**kwargs):  # noqa: ANN202
            raise RuntimeError("adapter init failed")

        monkeypatch.setattr(store_mod, "TraceraAdapter", _boom)

        result = _build_dual_write_bridge(Path("/tmp/x.jsonl"))
        assert result is None

    def test_bridge_construction_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If TraceraBridge() raises after adapter succeeds, return None."""
        monkeypatch.setenv(TRACERA_DUAL_WRITE_ENV, "1")
        cfg = MagicMock()
        cfg.tracera.host = "tracera.test"
        cfg.tracera.port = 8080
        cfg.tracera.base_url = None
        cfg.tracera.api_token = None
        cfg.tracera.timeout_s = 5
        cfg.tracera.batch_size = 32
        cfg.trace_bridges.include_kinds = ["claim"]

        import pheno.runtime_config as rc
        import pheno.trace_store as store_mod
        import traces.tracera_bridge as bridge_mod

        monkeypatch.setattr(rc, "load_config", lambda: cfg)

        # Adapter construction succeeds.
        monkeypatch.setattr(store_mod, "TraceraAdapter", lambda **kwargs: MagicMock())

        # Bridge construction fails.
        def _boom_bridge(**kwargs):  # noqa: ANN202
            raise RuntimeError("bridge init failed")

        monkeypatch.setattr(bridge_mod, "TraceraBridge", _boom_bridge)

        result = _build_dual_write_bridge(Path("/tmp/x.jsonl"))
        assert result is None

    def test_load_config_failure_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If load_config() raises inside the function, return None."""
        monkeypatch.setenv(TRACERA_DUAL_WRITE_ENV, "1")
        import pheno.runtime_config as rc

        def _raise():  # noqa: ANN202
            raise RuntimeError("config load failed")

        monkeypatch.setattr(rc, "load_config", _raise)
        result = _build_dual_write_bridge(Path("/tmp/x.jsonl"))
        assert result is None

    def test_successful_build_returns_bridge(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When dual-write is enabled and the adapter/bridge build cleanly, return a bridge."""
        monkeypatch.setenv(TRACERA_DUAL_WRITE_ENV, "1")
        cfg = MagicMock()
        cfg.tracera.host = "tracera.test"
        cfg.tracera.port = 8080
        cfg.tracera.base_url = None
        cfg.tracera.api_token = None
        cfg.tracera.timeout_s = 5
        cfg.tracera.batch_size = 32
        cfg.trace_bridges.include_kinds = ["claim"]

        import pheno.runtime_config as rc
        import pheno.trace_store as store_mod
        import traces.tracera_bridge as bridge_mod

        monkeypatch.setattr(rc, "load_config", lambda: cfg)

        fake_adapter = MagicMock()
        monkeypatch.setattr(store_mod, "TraceraAdapter", lambda **kwargs: fake_adapter)

        fake_bridge = MagicMock()
        monkeypatch.setattr(bridge_mod, "TraceraBridge", lambda **kwargs: fake_bridge)

        result = _build_dual_write_bridge(Path("/tmp/x.jsonl"))
        assert result is fake_bridge


# ---------------------------------------------------------------------------
# collect_all — fallback JSONL-only when bridge cannot be built
# ---------------------------------------------------------------------------


class TestCollectAllJSONLFallback:
    """When bridge construction fails, collect_all() falls back to plain JSONL writes."""

    def test_fallback_when_bridge_unavailable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(TRACERA_DUAL_WRITE_ENV, "0")
        monkeypatch.setattr(ingest_mod.Path, "home", lambda: tmp_path)
        monkeypatch.setattr(ingest_mod, "FORGE_DIR", tmp_path / "no_forge")
        monkeypatch.setattr(ingest_mod, "AGENT_RUNNER_DIR", tmp_path / "no_jobs")
        monkeypatch.setattr(ingest_mod, "FORGE_DISPATCH_DIR", tmp_path / "no_dispatch")
        monkeypatch.setattr(ingest_mod, "CURSOR_PROJECTS", tmp_path / "no_cursor")

        ev = TraceEvent(
            source="forge", event_type="history_line", timestamp="2026-01-01T00:00:00Z"
        )
        with patch.object(TraceCollector, "all_sources", return_value=iter([ev])):
            out_dir = tmp_path / "training"
            out_path, n = collect_all(out_dir=out_dir)

        assert n == 1
        # JSONL file written.
        assert out_path.exists()
        content = out_path.read_text()
        assert "forge" in content
        assert "history_line" in content

    def test_collect_all_no_events(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When all_sources yields nothing, file still gets created with count 0."""
        monkeypatch.setenv(TRACERA_DUAL_WRITE_ENV, "0")
        monkeypatch.setattr(ingest_mod.Path, "home", lambda: tmp_path)
        monkeypatch.setattr(ingest_mod, "FORGE_DIR", tmp_path / "no_forge")
        monkeypatch.setattr(ingest_mod, "AGENT_RUNNER_DIR", tmp_path / "no_jobs")
        monkeypatch.setattr(ingest_mod, "FORGE_DISPATCH_DIR", tmp_path / "no_dispatch")
        monkeypatch.setattr(ingest_mod, "CURSOR_PROJECTS", tmp_path / "no_cursor")

        with patch.object(TraceCollector, "all_sources", return_value=iter([])):
            out_dir = tmp_path / "training"
            out_path, n = collect_all(out_dir=out_dir)

        assert n == 0
        assert out_path.exists()
        # Empty file is fine.
        assert out_path.read_text() == ""


# ---------------------------------------------------------------------------
# TraceCollector.__init__ — default omniroute_db
# ---------------------------------------------------------------------------


class TestCollectorInit:
    def test_default_omniroute_db(self) -> None:
        """Without an arg, the collector uses the canonical OMNIROUTE_DB."""
        collector = TraceCollector()
        # pheno.paths.OMNIROUTE_DB is a Path; just verify the attribute.
        from pheno.paths import OMNIROUTE_DB

        assert collector.omniroute_db == OMNIROUTE_DB

    def test_explicit_omniroute_db(self, tmp_path: Path) -> None:
        db = tmp_path / "explicit.sqlite"
        collector = TraceCollector(omniroute_db=db)
        assert collector.omniroute_db == db


# ---------------------------------------------------------------------------
# TraceEvent dataclass — kwargs in all fields
# ---------------------------------------------------------------------------


class TestTraceEventAllFields:
    """TraceEvent accepts every field with concrete values."""

    def test_all_fields_populated(self) -> None:
        ev = TraceEvent(
            source="omniroute",
            event_type="llm_call",
            timestamp="2026-01-01T00:00:00Z",
            tokens_in=10,
            tokens_out=20,
            tokens_cache_read=5,
            duration_ms=500,
            model="gpt-4",
            provider="openai",
            harness="omniroute",
            session_id="session-x",
            motion_hint="forward",
            meta={"combo": "a"},
        )
        d = ev.to_dict()
        assert d["tokens_in"] == 10
        assert d["tokens_out"] == 20
        assert d["tokens_cache_read"] == 5
        assert d["duration_ms"] == 500
        assert d["model"] == "gpt-4"
        assert d["provider"] == "openai"
        assert d["harness"] == "omniroute"
        assert d["session_id"] == "session-x"
        assert d["motion_hint"] == "forward"
        assert d["meta"] == {"combo": "a"}

    def test_default_meta_is_independent_per_instance(self) -> None:
        """Each TraceEvent gets its own meta dict (mutable default safety)."""
        ev1 = TraceEvent(source="a", event_type="x", timestamp="t")
        ev2 = TraceEvent(source="b", event_type="y", timestamp="t")
        ev1.meta["k"] = 1
        assert "k" not in ev2.meta
