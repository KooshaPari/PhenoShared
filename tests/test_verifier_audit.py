"""Tests for verifier/audit.py — audit records + batch auditing."""
from __future__ import annotations

from verifier import audit as audit_mod
from verifier.audit import (
    AuditRecord,
    audit_batch,
    audit_trace,
    build_audit_record,
    gate_pass_rate,
    load_recent_audit,
    read_audit_log,
    reward_summary,
    verify_audit_consistency,
    write_audit_log,
)
from verifier.harness import VerifierResult
from verifier.rewards import RewardBreakdown


def _vr(**kw) -> VerifierResult:
    defaults = {"trace_id": "t1", "role": "patch", "ok": True, "checks": {}, "errors": [], "meta": {}}
    defaults.update(kw)
    return VerifierResult(**defaults)


def _rb(**kw) -> RewardBreakdown:
    defaults = {"total": 0.8, "passed": True, "json_valid": 1.0, "tests_pass": 1.0}
    defaults.update(kw)
    return RewardBreakdown(**defaults)


class TestAuditRecord:
    def test_to_dict(self):
        rec = AuditRecord(trace_id="t1", role="patch", ok=True, reward_total=0.9, tier="low")
        d = rec.to_dict()
        assert d["trace_id"] == "t1"
        assert d["ok"] is True
        assert d["tier"] == "low"
        assert "created_at" in d

    def test_default_created_at(self):
        rec = AuditRecord(trace_id="t1", role="patch", ok=True, reward_total=0.5, tier="none")
        assert rec.created_at  # not empty


class TestBuildAuditRecord:
    def test_passing(self):
        r = _vr(trace_id="tr1", role="plan", ok=True)
        rb = _rb(total=0.85, passed=True)
        rec = build_audit_record(r, rb)
        assert rec.trace_id == "tr1"
        assert rec.role == "plan"
        assert rec.ok is True
        assert rec.reward_total == 0.85

    def test_failing_when_verifier_fails(self):
        r = _vr(ok=False)
        rb = _rb(passed=True)
        rec = build_audit_record(r, rb)
        assert rec.ok is False

    def test_failing_when_reward_fails(self):
        r = _vr(ok=True)
        rb = _rb(passed=False, total=0.3)
        rec = build_audit_record(r, rb)
        assert rec.ok is False

    def test_tier_extraction(self):
        r = _vr(meta={"risky_action_tier": "high"})
        rb = _rb()
        rec = build_audit_record(r, rb)
        assert rec.tier == "high"

    def test_default_tier(self):
        r = _vr(meta={})
        rb = _rb()
        rec = build_audit_record(r, rb)
        assert rec.tier == "none"


class TestGatePassRate:
    def test_empty(self):
        assert gate_pass_rate([]) == 1.0

    def test_all_pass(self):
        results = [_vr(checks={"risky_action_gate": True}) for _ in range(5)]
        assert gate_pass_rate(results) == 1.0

    def test_one_fail(self):
        results = [
            _vr(checks={"risky_action_gate": True}),
            _vr(checks={"risky_action_gate": False}),
        ]
        assert gate_pass_rate(results) == 0.5

    def test_missing_check_passes(self):
        results = [_vr(checks={})]
        assert gate_pass_rate(results) == 1.0

    def test_all_fail(self):
        results = [_vr(checks={"risky_action_gate": False}) for _ in range(3)]
        assert gate_pass_rate(results) == 0.0


class TestRewardSummary:
    def test_empty(self):
        s = reward_summary([])
        assert s["count"] == 0
        assert s["mean_total"] == 0.0

    def test_single(self):
        rb = _rb(total=0.8, passed=True)
        s = reward_summary([rb])
        assert s["count"] == 1
        assert s["mean_total"] == 0.8
        assert s["pass_rate"] == 1.0

    def test_mixed(self):
        rb1 = _rb(total=0.9, passed=True, json_valid=1.0, tests_pass=1.0)
        rb2 = _rb(total=0.3, passed=False, json_valid=0.0, tests_pass=0.0)
        s = reward_summary([rb1, rb2])
        assert s["count"] == 2
        assert abs(s["mean_total"] - 0.6) < 0.01
        assert s["pass_rate"] == 0.5
        assert "by_dimension" in s


class TestWriteReadAuditLog:
    def test_roundtrip(self, tmp_path):
        p = tmp_path / "audit.jsonl"
        recs = [
            AuditRecord(trace_id="t1", role="patch", ok=True, reward_total=0.8, tier="low"),
            AuditRecord(trace_id="t2", role="plan", ok=False, reward_total=0.2, tier="high"),
        ]
        write_audit_log(recs, p)
        loaded = read_audit_log(p)
        assert len(loaded) == 2
        assert loaded[0].trace_id == "t1"
        assert loaded[1].ok is False

    def test_read_missing_file(self, tmp_path):
        p = tmp_path / "nonexistent.jsonl"
        assert read_audit_log(p) == []

    def test_write_empty(self, tmp_path):
        p = tmp_path / "empty.jsonl"
        write_audit_log([], p)
        assert p.exists()
        assert p.read_text() == ""


class TestAuditBatch:
    def test_batch(self):
        results = [_vr(trace_id="t1"), _vr(trace_id="t2")]
        rewards = [_rb(total=0.8, passed=True), _rb(total=0.6, passed=True)]
        b = audit_batch(results, rewards)
        assert b["count"] == 2
        assert "gate_pass_rate" in b
        assert "reward_summary" in b
        assert "timestamp" in b


class TestVerifyAuditConsistency:
    def test_valid_records(self):
        recs = [
            AuditRecord(trace_id="t1", role="patch", ok=True, reward_total=0.8, tier="low"),
        ]
        v = verify_audit_consistency(recs)
        assert v["valid"] is True
        assert v["errors"] == []

    def test_missing_trace_id(self):
        recs = [AuditRecord(trace_id="", role="patch", ok=True, reward_total=0.5, tier="none")]
        v = verify_audit_consistency(recs)
        assert v["valid"] is False
        assert any("trace_id" in e for e in v["errors"])

    def test_reward_out_of_range(self):
        recs = [AuditRecord(trace_id="t1", role="patch", ok=True, reward_total=2.0, tier="none")]
        v = verify_audit_consistency(recs)
        assert v["valid"] is False
        assert any("out of range" in e for e in v["errors"])

    def test_reward_negative(self):
        recs = [AuditRecord(trace_id="t1", role="patch", ok=True, reward_total=-0.1, tier="none")]
        v = verify_audit_consistency(recs)
        assert v["valid"] is False

    def test_unknown_tier(self):
        recs = [AuditRecord(trace_id="t1", role="patch", ok=True, reward_total=0.5, tier="invalid")]
        v = verify_audit_consistency(recs)
        assert v["valid"] is False
        assert any("unknown tier" in e for e in v["errors"])


class TestLoadRecentAudit:
    def test_empty_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(audit_mod, "TRAINING_DIR", tmp_path)
        recs = load_recent_audit()
        assert recs == []

    def test_limit(self, tmp_path, monkeypatch):
        p = tmp_path / "audit_log.jsonl"
        recs = [
            AuditRecord(trace_id=f"t{i}", role="patch", ok=True, reward_total=0.5, tier="none")
            for i in range(20)
        ]
        write_audit_log(recs, p)
        monkeypatch.setattr(audit_mod, "TRAINING_DIR", tmp_path)
        recent = load_recent_audit(limit=5)
        assert len(recent) == 5
        assert recent[0].trace_id == "t19"  # reversed, most recent first


class TestAuditTrace:
    def test_audit_trace_smoke(self):
        trace = {
            "id": "trace_test",
            "role": "patch",
            "response": '{"key": "value"}',
        }
        rec = audit_trace(trace)
        assert rec.trace_id == "trace_test"
        assert isinstance(rec.ok, bool)
