"""Tests for traces/motion.py — motion classification + ROI."""
from __future__ import annotations

from traces.motion import MotionClass, MotionScore, classify_motion, motion_roi


class TestMotionClass:
    def test_enum_values(self):
        assert MotionClass.FORWARD == "forward"
        assert MotionClass.STAGNATE == "stagnate"
        assert MotionClass.REGRESS == "regress"
        assert MotionClass.UNKNOWN == "unknown"

    def test_enum_members(self):
        assert set(MotionClass) == {
            MotionClass.FORWARD,
            MotionClass.STAGNATE,
            MotionClass.REGRESS,
            MotionClass.UNKNOWN,
        }


class TestMotionScore:
    def test_to_dict(self):
        ms = MotionScore(MotionClass.FORWARD, 0.8, ["productive_output"])
        d = ms.to_dict()
        assert d == {"motion": "forward", "roi": 0.8, "reasons": ["productive_output"]}

    def test_to_dict_stagnate(self):
        ms = MotionScore(MotionClass.STAGNATE, 0.2, ["repeated_error"])
        assert ms.to_dict()["motion"] == "stagnate"


class TestClassifyMotion:
    def test_http_error_regress(self):
        ev = {"meta": {"status": 500}}
        ms = classify_motion(ev)
        assert ms.motion == MotionClass.REGRESS
        assert ms.roi == 0.0

    def test_http_400_regress(self):
        ev = {"meta": {"status": 422}}
        ms = classify_motion(ev)
        assert ms.motion == MotionClass.REGRESS

    def test_job_failed_regress(self):
        ev = {"meta": {"state": "failed"}}
        ms = classify_motion(ev)
        assert ms.motion == MotionClass.REGRESS

    def test_job_error_regress(self):
        ev = {"meta": {"state": "error"}}
        ms = classify_motion(ev)
        assert ms.motion == MotionClass.REGRESS

    def test_repeated_error_stagnate(self):
        prev = {"meta": {"error_summary": "ConnectionRefused"}}
        ev = {"meta": {"error_summary": "ConnectionRefused"}}
        ms = classify_motion(ev, prev)
        assert ms.motion == MotionClass.STAGNATE
        assert ms.roi == 0.2

    def test_duplicate_context_stagnate(self):
        prev = {"tokens_in": 1000, "tokens_out": 10}
        ev = {"tokens_in": 1010, "tokens_out": 20}
        ms = classify_motion(ev, prev)
        assert ms.motion == MotionClass.STAGNATE
        assert ms.roi == 0.3

    def test_high_output_forward(self):
        ev = {"tokens_out": 200, "tokens_in": 500}
        ms = classify_motion(ev)
        assert ms.motion == MotionClass.FORWARD
        assert ms.roi > 0

    def test_completed_state_forward(self):
        ev = {"meta": {"state": "completed"}, "tokens_out": 50, "tokens_in": 100}
        ms = classify_motion(ev)
        assert ms.motion == MotionClass.FORWARD

    def test_some_output_forward(self):
        ev = {"tokens_out": 10}
        ms = classify_motion(ev)
        assert ms.motion == MotionClass.FORWARD
        assert ms.roi == 0.4

    def test_no_signal_unknown(self):
        ev = {}
        ms = classify_motion(ev)
        assert ms.motion == MotionClass.UNKNOWN
        assert ms.roi == 0.0

    def test_empty_response_unknown(self):
        ev = {"tokens_out": 0, "tokens_in": 0}
        ms = classify_motion(ev)
        assert ms.motion == MotionClass.UNKNOWN

    def test_200_status_does_not_regress(self):
        ev = {"meta": {"status": 200}, "tokens_out": 150}
        ms = classify_motion(ev)
        assert ms.motion == MotionClass.FORWARD


class TestMotionRoi:
    def test_empty_events(self):
        result = motion_roi([])
        assert result == {"forward": 0, "stagnate": 0, "regress": 0, "unknown": 0, "avg_roi": 0.0}

    def test_single_forward_event(self):
        events = [{"tokens_out": 200}]
        result = motion_roi(events)
        assert result["forward"] == 1.0
        assert result["total_events"] == 1

    def test_mixed_events(self):
        events = [
            {"tokens_out": 200},          # forward
            {"meta": {"status": 500}},      # regress
            {"meta": {"state": "failed"}},  # regress
            {},                              # unknown
        ]
        result = motion_roi(events)
        assert result["total_events"] == 4
        assert result["regress"] == 0.5
        assert result["forward"] == 0.25
        assert result["unknown"] == 0.25

    def test_repeated_error_stagnation(self):
        prev = {"meta": {"error_summary": "timeout"}}
        ev = {"meta": {"error_summary": "timeout"}}
        events = [prev, ev]
        result = motion_roi(events)
        assert result["stagnate"] == 0.5

    def test_all_forward(self):
        events = [{"tokens_out": 200} for _ in range(5)]
        result = motion_roi(events)
        assert result["forward"] == 1.0
        assert result["avg_roi"] > 0
