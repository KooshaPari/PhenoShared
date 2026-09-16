"""Tests for eval/tbench_v3_watch.py — TB3 watch state recording."""
from __future__ import annotations

import json

from eval.tbench_v3_watch import record_status


class TestRecordStatus:
    def test_default_disabled(self, tmp_path):
        output = tmp_path / "tb3_watch.jsonl"
        result = record_status(output=output)
        assert result == output
        assert output.exists()
        lines = output.read_text().strip().splitlines()
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["suite"] == "terminal-bench@3.x"
        assert rec["status"] == "disabled"
        assert rec["network_action"] == "none"

    def test_enabled_when_env_set(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PHENO_ENABLE_TB3", "1")
        output = tmp_path / "tb3_watch.jsonl"
        record_status(output=output)
        rec = json.loads(output.read_text().strip().splitlines()[0])
        assert rec["status"] == "watch_enabled_pending_registry_check"

    def test_disabled_when_env_unset(self, tmp_path, monkeypatch):
        monkeypatch.delenv("PHENO_ENABLE_TB3", raising=False)
        output = tmp_path / "tb3_watch.jsonl"
        record_status(output=output)
        rec = json.loads(output.read_text().strip().splitlines()[0])
        assert rec["status"] == "disabled"

    def test_disabled_when_env_wrong_value(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PHENO_ENABLE_TB3", "0")
        output = tmp_path / "tb3_watch.jsonl"
        record_status(output=output)
        rec = json.loads(output.read_text().strip().splitlines()[0])
        assert rec["status"] == "disabled"

    def test_appends_to_existing(self, tmp_path):
        output = tmp_path / "tb3_watch.jsonl"
        record_status(output=output)
        record_status(output=output)
        lines = output.read_text().strip().splitlines()
        assert len(lines) == 2

    def test_record_has_timestamp(self, tmp_path):
        output = tmp_path / "tb3_watch.jsonl"
        record_status(output=output)
        rec = json.loads(output.read_text().strip().splitlines()[0])
        assert "timestamp" in rec
        assert "2026" in rec["timestamp"]  # Sanity check

    def test_record_has_reason(self, tmp_path):
        output = tmp_path / "tb3_watch.jsonl"
        record_status(output=output)
        rec = json.loads(output.read_text().strip().splitlines()[0])
        assert "PHENO_ENABLE_TB3" in rec["reason"]
