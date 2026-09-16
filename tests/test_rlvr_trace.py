"""Tests for bench.rlvr_af.trace module — coverage sprint v0.35."""
from __future__ import annotations

import json
import time

import pytest

from bench.rlvr_af.trace import (
    Artifact,
    JudgeVerdict,
    Recorder,
    Trail,
    Transition,
)


class TestArtifact:
    """Artifact dataclass tests."""

    def test_default_construction(self) -> None:
        a = Artifact(elapsed_s=0.1, prompt="hi", completion="bye")
        assert a.elapsed_s == 0.1
        assert a.prompt == "hi"
        assert a.completion == "bye"
        assert a.expected is None
        assert a.tokens_in == 0
        assert a.tokens_out == 0
        assert a.raw == ""
        assert a.extra == {}

    def test_extra_field_is_independent_per_instance(self) -> None:
        """Each Artifact must get its own dict to avoid shared-mutable default."""
        a1 = Artifact(elapsed_s=0.1, prompt="x", completion="y")
        a2 = Artifact(elapsed_s=0.2, prompt="p", completion="q")
        a1.extra["k"] = "v"
        assert a2.extra == {}

    def test_full_construction(self) -> None:
        a = Artifact(
            elapsed_s=1.5,
            prompt="P",
            completion="C",
            expected="E",
            tokens_in=10,
            tokens_out=20,
            raw="raw text",
            extra={"k": 1},
        )
        assert a.expected == "E"
        assert a.tokens_in == 10
        assert a.tokens_out == 20
        assert a.raw == "raw text"
        assert a.extra == {"k": 1}


class TestJudgeVerdict:
    """JudgeVerdict dataclass tests."""

    def test_minimum_construction(self) -> None:
        v = JudgeVerdict(passed=True, reward=0.8)
        assert v.passed is True
        assert v.reward == 0.8
        assert v.strict is None
        assert v.loose is None
        assert v.reason == ""
        assert v.meta == {}

    def test_full_construction(self) -> None:
        v = JudgeVerdict(
            passed=False,
            reward=0.0,
            strict=True,
            loose=False,
            reason="bad output",
            meta={"model": "x"},
        )
        assert v.strict is True
        assert v.loose is False
        assert v.reason == "bad output"
        assert v.meta == {"model": "x"}


class TestTransition:
    """Transition dataclass tests."""

    def test_construction_with_artifact(self) -> None:
        art = Artifact(elapsed_s=0.1, prompt="p", completion="c")
        t = Transition(task_id="task1", artifact=art)
        assert t.task_id == "task1"
        assert t.artifact is art
        assert t.verdict is None
        assert t.debug == {}

    def test_construction_with_verdict(self) -> None:
        art = Artifact(elapsed_s=0.1, prompt="p", completion="c")
        v = JudgeVerdict(passed=True, reward=1.0)
        t = Transition(task_id="t", artifact=art, verdict=v, debug={"x": 1})
        assert t.verdict is v
        assert t.debug == {"x": 1}


class TestTrail:
    """Trail dataclass tests."""

    def test_construction_defaults(self) -> None:
        t = Trail(suite="s", model="m", run_id="r", seed=42)
        assert t.suite == "s"
        assert t.model == "m"
        assert t.run_id == "r"
        assert t.seed == 42
        assert t.started_at is not None
        assert t.committed_at is None
        assert t.transitions == []
        assert t.meta == {}

    def test_add_appends(self) -> None:
        t = Trail(suite="s", model="m", run_id="r", seed=42)
        art = Artifact(elapsed_s=0.1, prompt="p", completion="c")
        t.add(Transition(task_id="t1", artifact=art))
        assert len(t.transitions) == 1
        assert t.transitions[0].task_id == "t1"

    def test_add_after_commit_raises(self) -> None:
        t = Trail(suite="s", model="m", run_id="r", seed=42)
        t.commit()
        art = Artifact(elapsed_s=0.1, prompt="p", completion="c")
        with pytest.raises(RuntimeError, match="trail already committed"):
            t.add(Transition(task_id="t1", artifact=art))

    def test_commit_sets_committed_at(self) -> None:
        t = Trail(suite="s", model="m", run_id="r", seed=42)
        assert t.committed_at is None
        before = time.time()
        t.commit()
        after = time.time()
        assert t.committed_at is not None
        assert before <= t.committed_at <= after

    def test_rewards_filters_no_verdict(self) -> None:
        t = Trail(suite="s", model="m", run_id="r", seed=42)
        art = Artifact(elapsed_s=0.1, prompt="p", completion="c")
        t.add(Transition(task_id="t1", artifact=art, verdict=None))
        t.add(Transition(task_id="t2", artifact=art, verdict=JudgeVerdict(passed=True, reward=0.5)))
        t.add(Transition(task_id="t3", artifact=art, verdict=JudgeVerdict(passed=False, reward=0.0)))
        assert t.rewards == [0.5, 0.0]

    def test_rewards_empty(self) -> None:
        t = Trail(suite="s", model="m", run_id="r", seed=42)
        assert t.rewards == []

    def test_mean_reward_zero_for_empty(self) -> None:
        t = Trail(suite="s", model="m", run_id="r", seed=42)
        assert t.mean_reward == 0.0

    def test_mean_reward_correct(self) -> None:
        t = Trail(suite="s", model="m", run_id="r", seed=42)
        art = Artifact(elapsed_s=0.1, prompt="p", completion="c")
        t.add(Transition(task_id="t1", artifact=art, verdict=JudgeVerdict(passed=True, reward=0.6)))
        t.add(Transition(task_id="t2", artifact=art, verdict=JudgeVerdict(passed=True, reward=0.8)))
        assert t.mean_reward == pytest.approx(0.7)

    def test_pass_ratio_is_alias_for_mean_reward(self) -> None:
        t = Trail(suite="s", model="m", run_id="r", seed=42)
        assert t.pass_ratio == t.mean_reward

    def test_to_dict_basic(self) -> None:
        t = Trail(suite="s", model="m", run_id="r", seed=42)
        d = t.to_dict()
        assert d["suite"] == "s"
        assert d["model"] == "m"
        assert d["run_id"] == "r"
        assert d["seed"] == 42
        assert d["started_at"] is not None
        assert d["committed_at"] is None
        assert d["n"] == 0
        assert d["mean_reward"] == 0.0
        assert d["meta"] == {}
        assert d["transitions"] == []

    def test_to_dict_with_transitions(self) -> None:
        t = Trail(suite="s", model="m", run_id="r", seed=42)
        art = Artifact(elapsed_s=0.1, prompt="p", completion="c")
        t.add(Transition(task_id="t1", artifact=art, verdict=JudgeVerdict(passed=True, reward=0.9)))
        d = t.to_dict()
        assert d["n"] == 1
        assert d["mean_reward"] == 0.9
        assert len(d["transitions"]) == 1
        assert d["transitions"][0]["task_id"] == "t1"

    def test_to_json_returns_valid_json(self) -> None:
        t = Trail(suite="s", model="m", run_id="r", seed=42)
        art = Artifact(elapsed_s=0.1, prompt="p", completion="c")
        t.add(Transition(task_id="t1", artifact=art, verdict=JudgeVerdict(passed=True, reward=0.9)))
        s = t.to_json()
        d = json.loads(s)
        assert d["suite"] == "s"
        assert d["n"] == 1
        assert d["mean_reward"] == 0.9

    def test_to_json_custom_indent(self) -> None:
        t = Trail(suite="s", model="m", run_id="r", seed=42)
        s = t.to_json(indent=4)
        assert "    " in s  # 4-space indent

    def test_from_json_empty(self) -> None:
        t = Trail(suite="s", model="m", run_id="r", seed=42)
        s = t.to_json()
        t2 = Trail.from_json(s)
        assert t2.suite == "s"
        assert t2.model == "m"
        assert t2.run_id == "r"
        assert t2.seed == 42
        assert t2.transitions == []

    def test_from_json_with_transitions(self) -> None:
        t = Trail(suite="s", model="m", run_id="r", seed=42)
        art = Artifact(elapsed_s=0.1, prompt="p", completion="c", tokens_in=5)
        t.add(Transition(task_id="t1", artifact=art, verdict=JudgeVerdict(passed=True, reward=0.9, reason="ok")))
        s = t.to_json()
        t2 = Trail.from_json(s)
        assert t2.suite == "s"
        assert len(t2.transitions) == 1
        assert t2.transitions[0].task_id == "t1"
        assert t2.transitions[0].artifact.tokens_in == 5
        assert t2.transitions[0].verdict.reason == "ok"

    def test_from_json_transitions_without_verdict(self) -> None:
        t = Trail(suite="s", model="m", run_id="r", seed=42)
        art = Artifact(elapsed_s=0.1, prompt="p", completion="c")
        t.add(Transition(task_id="t1", artifact=art, verdict=None))
        s = t.to_json()
        t2 = Trail.from_json(s)
        assert t2.transitions[0].verdict is None

    def test_from_json_no_transitions_key(self) -> None:
        """Empty trail JSON may lack transitions key."""
        t = Trail(suite="s", model="m", run_id="r", seed=42)
        s = json.dumps({"suite": "s", "model": "m", "run_id": "r", "seed": 42, "started_at": 1.0})
        t2 = Trail.from_json(s)
        assert t2.transitions == []

    def test_from_json_no_meta_key(self) -> None:
        t = Trail(suite="s", model="m", run_id="r", seed=42)
        s = json.dumps({"suite": "s", "model": "m", "run_id": "r", "seed": 42, "started_at": 1.0})
        t2 = Trail.from_json(s)
        assert t2.meta == {}

    def test_from_json_no_committed_at(self) -> None:
        t = Trail(suite="s", model="m", run_id="r", seed=42)
        s = json.dumps({"suite": "s", "model": "m", "run_id": "r", "seed": 42, "started_at": 1.0})
        t2 = Trail.from_json(s)
        assert t2.committed_at is None


class TestRecorder:
    """Recorder context manager tests."""

    def test_enter_returns_trail(self) -> None:
        with Recorder("s", "m", "r", seed=42) as trail:
            assert isinstance(trail, Trail)
            assert trail.suite == "s"
            assert trail.model == "m"
            assert trail.run_id == "r"
            assert trail.seed == 42

    def test_exit_auto_commits(self) -> None:
        with Recorder("s", "m", "r", seed=42) as trail:
            assert trail.committed_at is None
        assert trail.committed_at is not None

    def test_exit_does_not_overwrite_explicit_commit(self) -> None:
        with Recorder("s", "m", "r", seed=42) as trail:
            trail.commit()
            first_time = trail.committed_at
            import time as t
            t.sleep(0.01)
        assert trail.committed_at == first_time

    def test_records_transitions(self) -> None:
        with Recorder("s", "m", "r", seed=42) as trail:
            art = Artifact(elapsed_s=0.1, prompt="p", completion="c")
            trail.add(Transition(task_id="t1", artifact=art))
            trail.add(Transition(task_id="t2", artifact=art))
        assert len(trail.transitions) == 2

    def test_default_seed(self) -> None:
        with Recorder("s", "m", "r") as trail:
            assert trail.seed == 42


class TestRoundTrip:
    """Full round-trip serialization tests."""

    def test_complex_trail_roundtrip(self) -> None:
        with Recorder("s", "m", "r", seed=99) as trail:
            trail.meta["config"] = {"key": "val"}
            art = Artifact(
                elapsed_s=1.5,
                prompt="hello",
                completion="world",
                expected="expected",
                tokens_in=10,
                tokens_out=20,
                raw="raw data",
                extra={"debug": True},
            )
            v = JudgeVerdict(passed=True, reward=0.8, strict=True, loose=False, reason="ok", meta={"m": 1})
            t = Transition(task_id="complex", artifact=art, verdict=v, debug={"trace_id": "abc"})
            trail.add(t)
            trail.commit()

        s = trail.to_json()
        trail2 = Trail.from_json(s)

        assert trail2.suite == trail.suite
        assert trail2.model == trail.model
        assert trail2.run_id == trail.run_id
        assert trail2.seed == trail.seed
        assert trail2.committed_at == trail.committed_at
        assert trail2.meta == trail.meta
        assert len(trail2.transitions) == 1
        t2 = trail2.transitions[0]
        assert t2.task_id == "complex"
        assert t2.artifact.prompt == "hello"
        assert t2.artifact.completion == "world"
        assert t2.artifact.tokens_in == 10
        assert t2.artifact.tokens_out == 20
        assert t2.artifact.raw == "raw data"
        assert t2.artifact.extra == {"debug": True}
        assert t2.verdict.passed is True
        assert t2.verdict.reward == 0.8
        assert t2.verdict.strict is True
        assert t2.verdict.loose is False
        assert t2.verdict.reason == "ok"
        assert t2.verdict.meta == {"m": 1}
        assert t2.debug == {"trace_id": "abc"}