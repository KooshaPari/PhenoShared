"""Tests for traces/wastage.py — wastage detection + recommendations."""
from __future__ import annotations

import json

from traces.wastage import WastageReport, _load_jsonl, analyze_file, analyze_wastage


class TestWastageReport:
    def test_to_dict(self):
        r = WastageReport(generated_at="2026-01-01T00:00:00Z")
        d = r.to_dict()
        assert d["generated_at"] == "2026-01-01T00:00:00Z"
        assert d["total_events"] == 0
        assert d["recommendations"] == []

    def test_to_dict_with_data(self):
        r = WastageReport(
            generated_at="now",
            total_events=10,
            giant_calls_32k_plus=2,
            overlap_waste_rate=0.3,
            recommendations=["fix this"],
        )
        d = r.to_dict()
        assert d["giant_calls_32k_plus"] == 2
        assert d["overlap_waste_rate"] == 0.3
        assert d["recommendations"] == ["fix this"]


class TestAnalyzeWastage:
    def test_empty_events(self):
        report = analyze_wastage([])
        assert report.total_events == 0
        assert report.total_tokens_in == 0
        assert report.recommendations == []

    def test_single_event(self):
        events = [{"tokens_in": 100, "tokens_out": 50, "source": "forge"}]
        report = analyze_wastage(events)
        assert report.total_events == 1
        assert report.total_tokens_in == 100
        assert report.total_tokens_out == 50
        assert report.by_source["forge"] == 1

    def test_giant_call_detection(self):
        events = [{"tokens_in": 40000}]
        report = analyze_wastage(events)
        assert report.giant_calls_32k_plus == 1
        assert len(report.recommendations) > 0
        assert "32k" in report.recommendations[0].lower() or "context" in report.recommendations[0].lower()

    def test_multiple_providers(self):
        events = [
            {"provider": "openai", "tokens_in": 100},
            {"provider": "anthropic", "tokens_in": 200},
            {"provider": "openai", "tokens_in": 150},
        ]
        report = analyze_wastage(events)
        assert report.by_provider.get("openai", 0) == 250
        assert report.by_provider.get("anthropic", 0) == 200

    def test_duplicate_context_clusters(self):
        events = [
            {"tokens_in": 4096, "session_id": "a"},
            {"tokens_in": 4096, "session_id": "b"},
            {"tokens_in": 4096, "session_id": "c"},
            {"tokens_in": 4096, "session_id": "d"},
            {"tokens_in": 4096, "session_id": "e"},
        ]
        report = analyze_wastage(events)
        assert report.duplicate_context_clusters >= 1

    def test_high_overlap_recommendation(self):
        events = [
            {"tokens_in": 8192, "session_id": str(i), "source": "omniroute"}
            for i in range(6)
        ]
        report = analyze_wastage(events)
        assert report.overlap_waste_rate > 0.15
        assert any("dedupe" in r.lower() for r in report.recommendations)

    def test_cache_read_recommendation(self):
        events = [{"tokens_in": 100, "tokens_cache_read": 80}]
        report = analyze_wastage(events)
        assert any("cache" in r.lower() for r in report.recommendations)

    def test_regress_rate_recommendation(self):
        events = [
            {"meta": {"status": 500}, "source": "omniroute"},
            {"meta": {"status": 200}, "tokens_out": 200, "source": "omniroute"},
        ]
        report = analyze_wastage(events)
        assert report.motion.get("regress", 0) > 0.10
        assert any("regress" in r.lower() for r in report.recommendations)

    def test_by_source_multiple(self):
        events = [
            {"source": "forge", "tokens_in": 50},
            {"source": "forge", "tokens_in": 50},
            {"source": "codex", "tokens_in": 50},
        ]
        report = analyze_wastage(events)
        assert report.by_source["forge"] == 2
        assert report.by_source["codex"] == 1


class TestLoadJsonl:
    def test_load_jsonl(self, tmp_path):
        p = tmp_path / "test.jsonl"
        p.write_text('{"a": 1}\n{"b": 2}\n\n{"c": 3}\n')
        rows = _load_jsonl(p)
        assert len(rows) == 3
        assert rows[0] == {"a": 1}
        assert rows[2] == {"c": 3}

    def test_load_jsonl_empty(self, tmp_path):
        p = tmp_path / "empty.jsonl"
        p.write_text("")
        rows = _load_jsonl(p)
        assert rows == []


class TestAnalyzeFile:
    def test_analyze_file(self, tmp_path):
        p = tmp_path / "trace.jsonl"
        p.write_text(json.dumps({"tokens_in": 100, "tokens_out": 50}) + "\n")
        report = analyze_file(p)
        assert report.total_events == 1
        assert report.total_tokens_in == 100
