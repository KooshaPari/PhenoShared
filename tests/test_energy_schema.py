"""Tests for bench/energy_schema.py — EnergyResult dataclass."""
from __future__ import annotations

import json

from bench.energy_schema import EnergyResult

SAMPLE = {
    "model": "llama-7b",
    "backend": "vllm",
    "suite": "mt-bench",
    "task_id": "q1",
    "latency_ms": 123.4,
    "tokens_per_sec": 42.0,
    "energy_mj": 56.7,
    "energy_per_token_mj": 1.35,
    "peak_rss_mb": 8192.0,
}


def _make(**overrides) -> EnergyResult:
    d = {**SAMPLE, **overrides}
    return EnergyResult(**d)


class TestEnergyResultRoundTrip:
    def test_to_dict(self):
        er = _make()
        d = er.to_dict()
        assert isinstance(d, dict)
        assert d["model"] == "llama-7b"
        assert d["latency_ms"] == 123.4
        assert d["extra"] == {}

    def test_to_dict_with_extra(self):
        er = _make(extra={"gpu_util": 0.95})
        d = er.to_dict()
        assert d["extra"]["gpu_util"] == 0.95

    def test_to_json(self):
        er = _make()
        j = er.to_json()
        parsed = json.loads(j)
        assert parsed["model"] == "llama-7b"
        assert isinstance(parsed, dict)

    def test_from_dict(self):
        er = EnergyResult.from_dict(SAMPLE)
        assert er.model == "llama-7b"
        assert er.energy_per_token_mj == 1.35

    def test_from_dict_ignores_unknown_keys(self):
        d = {**SAMPLE, "unknown_field": "skip", "extra_key": 42}
        er = EnergyResult.from_dict(d)
        assert er.model == "llama-7b"
        assert not hasattr(er, "unknown_field")

    def test_roundtrip_dict(self):
        original = _make()
        restored = EnergyResult.from_dict(original.to_dict())
        assert original == restored

    def test_roundtrip_json(self):
        original = _make()
        j = original.to_json()
        restored = EnergyResult.from_dict(json.loads(j))
        assert original == restored

    def test_default_extra_is_empty_dict(self):
        er = _make()
        assert er.extra == {}

    def test_default_extra_is_independent(self):
        er1 = _make()
        er2 = _make()
        er1.extra["x"] = 1
        assert "x" not in er2.extra
