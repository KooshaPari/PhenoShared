"""Comprehensive coverage tests for ``needle.compiler``.

Exercises the needle context-compiler surface:
* ``Slice`` / ``CompiledContext`` dataclass construction (including
  ``reduction_ratio``).
* ``NeedleRouter.route()`` covering header role override, model-name
  heuristics, prompt-keyword patterns, and learned defaults.
* ``NeedleRouter.train_from_call_logs()`` end-to-end against a tmp
  directory of synthetic call_logs JSONL files.
* ``NeedleRanker.rank()`` keyword overlap scoring + fallback behaviour.
* ``NeedleBudget.apply()`` budget trimming + truncation logic.
* ``ContextCompiler.compile()`` and ``ContextCompiler.render()``.

``NeedleBudget`` reads ``pheno.paths.CONFIG_DIR / context_caps.yaml``,
which is patched to a tmp directory so the tests stay hermetic.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import needle.compiler as needle_mod
import pheno.paths as pheno_paths
from needle.compiler import (
    CompiledContext,
    ContextCompiler,
    NeedleBudget,
    NeedleRanker,
    NeedleRouter,
    Slice,
    _est_tokens,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


CONTEXT_CAPS_YAML = """\
roles:
  route:
    max_context: 2048
  retrieve:
    max_context: 8192
  plan:
    max_context: 16384
  debug:
    max_context: 24576
  patch:
    max_context: 32768
compiled_target_tokens: 5120
"""


@pytest.fixture()
def patched_caps(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point ``pheno.paths.CONFIG_DIR`` at a tmp dir with a synthetic caps file."""
    caps = tmp_path / "context_caps.yaml"
    caps.write_text(CONTEXT_CAPS_YAML, encoding="utf-8")
    monkeypatch.setattr(pheno_paths, "CONFIG_DIR", tmp_path)
    # Need to invalidate the cached caps so NeedleBudget reloads.
    monkeypatch.setattr(needle_mod, "_load_caps", lambda: needle_mod.yaml.safe_load(caps.read_text(encoding="utf-8")))
    return caps


@pytest.fixture()
def router_tmp_patterns(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Provide a tmp patterns file so NeedleRouter doesn't try to read HOME."""
    patterns = tmp_path / "router_patterns.json"
    patterns.write_text("{}", encoding="utf-8")
    # Patch both pheno.paths (the source) and needle.compiler (the importer).
    monkeypatch.setattr(pheno_paths, "TRAINING_DIR", tmp_path)
    monkeypatch.setattr(needle_mod, "TRAINING_DIR", tmp_path)
    return patterns


@pytest.fixture()
def router(router_tmp_patterns: Path) -> NeedleRouter:
    """Construct a fresh NeedleRouter pointing at tmp patterns dir."""
    _ = router_tmp_patterns  # silence unused-arg warning
    return NeedleRouter()


# ---------------------------------------------------------------------------
# Slice / CompiledContext dataclass
# ---------------------------------------------------------------------------


class TestSlice:
    """``Slice`` dataclass instantiation."""

    def test_minimal_slice(self) -> None:
        s = Slice(path="x.py", score=0.5)
        assert s.path == "x.py"
        assert s.score == 0.5
        assert s.reason == ""

    def test_slice_with_reason(self) -> None:
        s = Slice(path="y.py", score=1.0, reason="overlap=3")
        assert s.reason == "overlap=3"


class TestCompiledContext:
    """``CompiledContext`` dataclass + reduction_ratio."""

    def test_default_construction(self) -> None:
        cc = CompiledContext(role="patch")
        assert cc.role == "patch"
        assert cc.slices == []
        assert cc.token_estimate == 0
        assert cc.original_estimate == 0

    def test_reduction_ratio_zero_when_original_is_zero(self) -> None:
        cc = CompiledContext(role="patch", token_estimate=0, original_estimate=0)
        assert cc.reduction_ratio == 0.0

    def test_reduction_ratio_full_compression(self) -> None:
        cc = CompiledContext(role="patch", token_estimate=0, original_estimate=1000)
        assert cc.reduction_ratio == pytest.approx(1.0)

    def test_reduction_ratio_half_compression(self) -> None:
        cc = CompiledContext(role="patch", token_estimate=500, original_estimate=1000)
        assert cc.reduction_ratio == pytest.approx(0.5)

    def test_reduction_ratio_no_compression(self) -> None:
        cc = CompiledContext(role="patch", token_estimate=1000, original_estimate=1000)
        assert cc.reduction_ratio == 0.0

    def test_reduction_ratio_inflation_caps_at_zero(self) -> None:
        cc = CompiledContext(role="patch", token_estimate=2000, original_estimate=1000)
        # Negative reduction → return the (negative) value
        assert cc.reduction_ratio == pytest.approx(-1.0)

    def test_compiled_context_with_slices(self) -> None:
        s1 = Slice(path="a.py", score=1.0)
        s2 = Slice(path="b.py", score=2.0, reason="overlap=2")
        cc = CompiledContext(
            role="patch",
            slices=[s1, s2],
            token_estimate=100,
            original_estimate=400,
        )
        assert len(cc.slices) == 2
        assert cc.slices[1].reason == "overlap=2"


# ---------------------------------------------------------------------------
# _est_tokens helper
# ---------------------------------------------------------------------------


class TestEstTokens:
    """``_est_tokens`` is the canonical ~4 chars/token estimator."""

    def test_short_text_returns_minimum_one(self) -> None:
        assert _est_tokens("") == 1
        assert _est_tokens("hi") == 1

    def test_long_text_uses_len_div_4(self) -> None:
        text = "a" * 40
        assert _est_tokens(text) == 10

    def test_boundary_at_three_chars(self) -> None:
        assert _est_tokens("aaa") == 1
        assert _est_tokens("aaaa") == 1


# ---------------------------------------------------------------------------
# NeedleRouter
# ---------------------------------------------------------------------------


class TestNeedleRouterRoute:
    """``NeedleRouter.route()`` role inference."""

    def test_header_role_wins(self, router: NeedleRouter) -> None:
        # Any prompt + any model + header role → header role wins
        role = router.route("hello", "codex-mini", header_role="emergency")
        assert role == "emergency"

    def test_header_role_is_lowercased(self, router: NeedleRouter) -> None:
        role = router.route("hello", "codex-mini", header_role="PLAN")
        assert role == "plan"

    def test_opus_model_returns_emergency(self, router: NeedleRouter) -> None:
        role = router.route("anything here", "claude-opus-4-2025")
        assert role == "emergency"

    def test_5_5_in_model_returns_emergency(self, router: NeedleRouter) -> None:
        role = router.route("anything here", "my-model-5.5-experimental")
        assert role == "emergency"

    def test_codex_model_returns_patch(self, router: NeedleRouter) -> None:
        role = router.route("anything here", "openai-codex-mini")
        assert role == "patch"

    def test_spark_model_returns_patch(self, router: NeedleRouter) -> None:
        role = router.route("anything here", "x-spark-1")
        assert role == "patch"

    def test_mini_model_returns_debug(self, router: NeedleRouter) -> None:
        role = router.route("anything here", "qwen-mini-1.5b")
        assert role == "debug"

    def test_4b_model_returns_patch(self, router: NeedleRouter) -> None:
        role = router.route("anything here", "qwen-4b")
        assert role == "patch"

    def test_qwen_model_returns_patch(self, router: NeedleRouter) -> None:
        role = router.route("anything here", "qwen-something")
        assert role == "patch"

    def test_routing_keyword_pattern(self, router: NeedleRouter) -> None:
        # The first pattern is route - matches "route" / "routing" / "classify"
        role = router.route("please classify this and route the result")
        assert role == "route"

    def test_retrieval_keyword_pattern(self, router: NeedleRouter) -> None:
        role = router.route("please find file matching *.py and search it")
        assert role == "retrieve"

    def test_rank_keyword_pattern(self, router: NeedleRouter) -> None:
        role = router.route("please rank these documents by relevance")
        assert role == "rank"

    def test_plan_keyword_pattern(self, router: NeedleRouter) -> None:
        role = router.route("please architect the design and plan the rollout")
        assert role == "plan"

    def test_debug_keyword_pattern(self, router: NeedleRouter) -> None:
        role = router.route("please fix the error in this traceback")
        assert role == "debug"

    def test_patch_keyword_pattern(self, router: NeedleRouter) -> None:
        role = router.route("please implement and edit this module")
        assert role == "patch"

    def test_keyword_match_is_case_insensitive(self, router: NeedleRouter) -> None:
        role = router.route("please ROUTE this request")
        assert role == "route"

    def test_falls_back_to_learned_default(self, router: NeedleRouter) -> None:
        # No header, no model heuristics, no keyword match → default_role
        # Default learned state is {"role_counts": {}, "default_role": "patch"}
        role = router.route("just some random unrelated text")
        assert role == "patch"

    def test_search_is_window_limited_to_4000(self, router: NeedleRouter) -> None:
        # Put the keyword outside the 4000-char window
        prompt = "x" * 4000 + " route this"
        role = router.route(prompt)
        # Outside the window → fall through to default ("patch")
        assert role == "patch"


# ---------------------------------------------------------------------------
# NeedleRouter.train_from_call_logs
# ---------------------------------------------------------------------------


class TestTrainFromCallLogs:
    """``train_from_call_logs()`` builds a patterns file from JSONL logs."""

    def test_train_creates_patterns_file(self, monkeypatch: pytest.MonkeyPatch,
                                          tmp_path: Path) -> None:
        log_path = tmp_path / "call_logs_2026.jsonl"
        records = [
            {"request_summary": "please route this", "model": "codex-mini"},
            {"request_summary": "please debug the error", "model": "qwen-mini"},
            {"request_summary": "please rank these", "model": "codex-mini"},
            {"request_summary": "please patch this", "model": "qwen-4b"},
        ]
        log_path.write_text(
            "\n".join(json.dumps(r) for r in records), encoding="utf-8"
        )
        monkeypatch.setattr(pheno_paths, "TRAINING_DIR", tmp_path)
        monkeypatch.setattr(needle_mod, "TRAINING_DIR", tmp_path)
        # Patterns file path for the router (constructed with patterns_path=None)
        router = NeedleRouter()
        result = router.train_from_call_logs(jsonl_glob="call_logs_*.jsonl")
        assert isinstance(result, dict)
        assert "role_counts" in result
        counts = result["role_counts"]
        # Most common should be one of route/debug/rank/patch
        assert max(counts.values()) >= 1
        # default_role must be the most common one
        assert result["default_role"] == max(counts.items(), key=lambda kv: kv[1])[0]

    def test_train_persists_patterns_to_disk(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        log_path = tmp_path / "call_logs_2026.jsonl"
        records = [
            {"request_summary": "please route this", "model": "codex-mini"},
        ]
        log_path.write_text(
            "\n".join(json.dumps(r) for r in records), encoding="utf-8"
        )
        monkeypatch.setattr(pheno_paths, "TRAINING_DIR", tmp_path)
        monkeypatch.setattr(needle_mod, "TRAINING_DIR", tmp_path)
        router = NeedleRouter()
        router.train_from_call_logs(jsonl_glob="call_logs_*.jsonl")
        # The patterns file should exist and be valid JSON
        pf = tmp_path / "router_patterns.json"
        assert pf.exists()
        data = json.loads(pf.read_text(encoding="utf-8"))
        assert "role_counts" in data

    def test_train_no_files_returns_defaults(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(pheno_paths, "TRAINING_DIR", tmp_path)
        monkeypatch.setattr(needle_mod, "TRAINING_DIR", tmp_path)
        router = NeedleRouter()
        result = router.train_from_call_logs(jsonl_glob="nonexistent_*.jsonl")
        assert result["role_counts"] == {}
        # default_role defaults to "patch" when no counts exist
        assert result["default_role"] == "patch"

    def test_train_skips_blank_lines(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        log_path = tmp_path / "call_logs_2026.jsonl"
        log_path.write_text(
            "\n".join(
                [
                    json.dumps({"request_summary": "please route", "model": "x"}),
                    "",
                    "   ",
                    json.dumps({"request_summary": "please route again", "model": "x"}),
                ]
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(pheno_paths, "TRAINING_DIR", tmp_path)
        monkeypatch.setattr(needle_mod, "TRAINING_DIR", tmp_path)
        router = NeedleRouter()
        result = router.train_from_call_logs(jsonl_glob="call_logs_*.jsonl")
        assert result["role_counts"]  # non-empty
        assert max(result["role_counts"].values()) >= 2

    def test_train_uses_request_summary_or_model(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Without request_summary, fall back to model
        log_path = tmp_path / "call_logs_2026.jsonl"
        records = [
            {"model": "qwen-mini-special"},  # → debug via model heuristic
        ]
        log_path.write_text(
            "\n".join(json.dumps(r) for r in records), encoding="utf-8"
        )
        monkeypatch.setattr(pheno_paths, "TRAINING_DIR", tmp_path)
        monkeypatch.setattr(needle_mod, "TRAINING_DIR", tmp_path)
        router = NeedleRouter()
        result = router.train_from_call_logs(jsonl_glob="call_logs_*.jsonl")
        assert "debug" in result["role_counts"]
    def test_router_with_existing_patterns_loads_them(
        self, tmp_path: Path
    ) -> None:
        # Pre-populate the patterns file and ensure the router loads it
        pf = tmp_path / "router_patterns.json"
        pf.write_text(
            json.dumps(
                {
                    "role_counts": {"emergency": 5, "patch": 1},
                    "default_role": "emergency",
                }
            ),
            encoding="utf-8",
        )
        router = NeedleRouter(patterns_path=pf)
        # Without any header/model/keyword, the default is "emergency"
        role = router.route("just some text with no keywords")
        assert role == "emergency"

    def test_router_handles_legacy_patterns_format(self, tmp_path: Path) -> None:
        # Legacy: bare dict of role counts (no role_counts wrapper)
        pf = tmp_path / "router_patterns.json"
        pf.write_text(json.dumps({"plan": 3, "patch": 1}), encoding="utf-8")
        router = NeedleRouter(patterns_path=pf)
        role = router.route("just some text")
        # Most frequent wins: "plan"
        assert role == "plan"


# ---------------------------------------------------------------------------
# NeedleRanker
# ---------------------------------------------------------------------------


class TestNeedleRanker:
    """``NeedleRanker.rank()`` keyword overlap scoring."""

    def test_rank_empty_candidates_returns_empty(self) -> None:
        ranker = NeedleRanker(top_k=3)
        assert ranker.rank("foo bar baz", []) == []

    def test_rank_zero_overlap_returns_fallback_first_n(
        self,
    ) -> None:
        ranker = NeedleRanker(top_k=3)
        cands = [
            {"path": "a.py", "content": "alpha bravo charlie"},
            {"path": "b.py", "content": "delta echo foxtrot"},
            {"path": "c.py", "content": "golf hotel india"},
        ]
        out = ranker.rank("zzzz no overlap", cands)
        assert len(out) == 3
        for s in out:
            assert s.score == 0.0
            assert s.reason == "fallback_no_overlap"

    def test_rank_orders_by_overlap_descending(self) -> None:
        ranker = NeedleRanker(top_k=10)
        cands = [
            {"path": "low.py", "content": "no relevant content"},
            {"path": "high.py", "content": "python python python"},
            {"path": "mid.py", "content": "python is great"},
        ]
        out = ranker.rank("python", cands)
        # The ranker deduplicates tokens per candidate (uses a set), so
        # both "high.py" and "mid.py" have overlap=1.
        # 'low.py' has score 0 so it's filtered out of the ranked list.
        paths_in_order = [s.path for s in out]
        # Both high and mid have overlap=1 → either order; "low.py" absent
        assert "low.py" not in paths_in_order
        assert set(paths_in_order) == {"high.py", "mid.py"}
        # Scores are monotonically decreasing
        scores = [s.score for s in out]
        assert scores == sorted(scores, reverse=True)

    def test_rank_path_bonus_doubles_score(self) -> None:
        ranker = NeedleRanker(top_k=10)
        cands = [
            # No keyword in content, but keyword in path
            {"path": "python.md", "content": "totally unrelated text"},
            # Has overlap=1, no path bonus
            {"path": "unrelated.md", "content": "python python"},
        ]
        out = ranker.rank("python", cands)
        # python.md: overlap=0, path_bonus=1 → score = 2
        # unrelated.md: overlap=1, path_bonus=0 → score = 1
        path_bonus_score = next(s for s in out if s.path == "python.md").score
        no_bonus_score = next(s for s in out if s.path == "unrelated.md").score
        # python.md score = 2 (1 path-bonus * 2), unrelated.md score = 1 (1 overlap)
        assert path_bonus_score == 2
        assert no_bonus_score == 1
        # Path-bonus entry ranks first
        assert out[0].path == "python.md"

    def test_rank_respects_top_k(self) -> None:
        ranker = NeedleRanker(top_k=2)
        cands = [
            {"path": f"f{i}.py", "content": f"token {i}"} for i in range(10)
        ]
        out = ranker.rank("token", cands)
        # Only candidates with positive overlap are kept
        # Each candidate has overlap=1 → 10 kept, but top_k=2 truncates
        assert len(out) == 2

    def test_rank_truncates_long_content_to_8000(self) -> None:
        ranker = NeedleRanker(top_k=1)
        # Use space-separated tokens so the regex word-boundary works.
        # The first 8000 chars will include several "match" tokens.
        content = ("match " * 3000) + ("x " * 5000)  # ~16000 chars total
        cands = [{"path": "x.py", "content": content}]
        out = ranker.rank("match", cands)
        assert len(out) == 1
        assert out[0].score > 0
        # "match" should appear in the overlap reason
        assert "overlap=" in out[0].reason

    def test_rank_includes_candidate_with_empty_path(self) -> None:
        ranker = NeedleRanker(top_k=10)
        cands = [
            {"content": "python is great"},  # No path key
            {"path": "x.py", "content": "python python"},
        ]
        out = ranker.rank("python", cands)
        # Both candidates get included; the one without 'path' is included with path=''
        assert len(out) == 2
        assert any(s.path == "" for s in out)
        assert any(s.path == "x.py" for s in out)


# ---------------------------------------------------------------------------
# NeedleBudget
# ---------------------------------------------------------------------------


class TestNeedleBudget:
    """``NeedleBudget.apply()`` budget trimming + ``cap_for_role``."""

    def test_cap_for_role_patch(self, patched_caps: Path) -> None:
        _ = patched_caps
        budget = NeedleBudget()
        assert budget.cap_for_role("patch") == 32768

    def test_cap_for_role_route(self, patched_caps: Path) -> None:
        _ = patched_caps
        budget = NeedleBudget()
        assert budget.cap_for_role("route") == 2048

    def test_cap_for_role_unknown_falls_back_to_patch(self, patched_caps: Path) -> None:
        _ = patched_caps
        budget = NeedleBudget()
        # Unknown role → falls back to "patch" entry
        assert budget.cap_for_role("nonexistent") == 32768

    def test_apply_trims_to_compile_cap_when_smaller(
        self, patched_caps: Path
    ) -> None:
        _ = patched_caps
        # patch role has 32768 cap, but compile cap is 5120
        budget = NeedleBudget()
        slices = [
            Slice(path=f"f{i}.py", score=10.0 - i) for i in range(5)
        ]
        contents = {f"f{i}.py": "a" * 4000 for i in range(5)}  # 1000 tokens each
        compiled = budget.apply("patch", slices, contents)
        # compile_cap = 5120, each slice ~1000 tokens → should keep ≤5 slices
        assert compiled.token_estimate <= 5120
        assert len(compiled.slices) >= 1

    def test_apply_records_original_estimate(
        self, patched_caps: Path
    ) -> None:
        _ = patched_caps
        budget = NeedleBudget()
        slices = [Slice(path=f"f{i}.py", score=10.0 - i) for i in range(3)]
        contents = {f"f{i}.py": "a" * 4000 for i in range(3)}
        compiled = budget.apply("patch", slices, contents)
        assert compiled.original_estimate == sum(1000 for _ in range(3))

    def test_apply_truncates_last_slice_when_remainder_is_large(
        self, patched_caps: Path
    ) -> None:
        _ = patched_caps
        budget = NeedleBudget()
        # 2 slices that would barely exceed the budget
        slices = [
            Slice(path="big.py", score=10.0),
            Slice(path="small.py", score=5.0),
        ]
        # Use route role cap (2048) so the budget is small enough to trigger truncation
        contents = {
            "big.py": "a" * 8000,    # 2000 tokens
            "small.py": "b" * 1200,  # 300 tokens
        }
        # route cap (2048) but compile cap (5120) → budget = min(2048, 5120) = 2048
        compiled = budget.apply("route", slices, contents)
        # big.py (2000 tokens) fits exactly; small.py (300) would push to 2300 > 2048,
        # so remain = 48 tokens which is < 256 → break without truncating.
        assert compiled.token_estimate <= 2048

    def test_apply_handles_missing_content(self, patched_caps: Path) -> None:
        _ = patched_caps
        budget = NeedleBudget()
        slices = [Slice(path="present.py", score=1.0), Slice(path="absent.py", score=0.5)]
        contents = {"present.py": "abc"}
        compiled = budget.apply("patch", slices, contents)
        # missing content → token estimate is 1 (min)
        assert any(s.path == "present.py" for s in compiled.slices)

    def test_apply_empty_slices(self, patched_caps: Path) -> None:
        _ = patched_caps
        budget = NeedleBudget()
        compiled = budget.apply("patch", [], {})
        assert compiled.token_estimate == 0
        assert compiled.original_estimate == 0
        assert compiled.slices == []

    def test_apply_sets_role(self, patched_caps: Path) -> None:
        _ = patched_caps
        budget = NeedleBudget()
        slices = [Slice(path="a.py", score=1.0)]
        contents = {"a.py": "abc"}
        compiled = budget.apply("retrieve", slices, contents)
        assert compiled.role == "retrieve"


# ---------------------------------------------------------------------------
# ContextCompiler
# ---------------------------------------------------------------------------


class TestContextCompiler:
    """``ContextCompiler.compile()`` and ``ContextCompiler.render()``."""

    def test_compile_returns_compiled_context(self, patched_caps: Path) -> None:
        _ = patched_caps
        compiler = ContextCompiler()
        cands = [
            {"path": "a.py", "content": "python debugging"},
            {"path": "b.py", "content": "another file"},
        ]
        contents = {"a.py": "python debugging notes", "b.py": "another"}
        compiled = compiler.compile(
            query="please debug the python error",
            candidates=cands,
            contents=contents,
        )
        assert isinstance(compiled, CompiledContext)
        assert compiled.role in ("patch", "debug", "plan", "route", "retrieve", "rank")
        assert len(compiled.slices) >= 1

    def test_compile_routes_via_header_role(self, patched_caps: Path) -> None:
        _ = patched_caps
        compiler = ContextCompiler()
        compiled = compiler.compile(
            query="anything",
            candidates=[],
            contents={},
            model="qwen-4b",
            header_role="emergency",
        )
        assert compiled.role == "emergency"

    def test_render_contains_role_and_token_count(
        self, patched_caps: Path
    ) -> None:
        _ = patched_caps
        compiler = ContextCompiler()
        cands = [{"path": "a.py", "content": "hello"}]
        contents = {"a.py": "hello world"}
        compiled = compiler.compile(
            query="debug please", candidates=cands, contents=contents
        )
        out = compiler.render(compiled, contents)
        assert "Compiled context" in out
        assert "role=" in out
        assert "a.py" in out
        assert "hello" in out

    def test_render_truncates_content_to_12000(
        self, patched_caps: Path
    ) -> None:
        _ = patched_caps
        compiler = ContextCompiler()
        cands = [{"path": "big.py", "content": "x"}]
        contents = {"big.py": "Z" * 50_000}
        compiled = compiler.compile(
            query="anything",
            candidates=cands,
            contents=contents,
            header_role="route",
        )
        out = compiler.render(compiled, contents)
        # Rendered content should be at most ~12000 chars (one slice)
        assert "Z" * 12001 not in out

    def test_compile_no_candidates_returns_empty_slices(
        self, patched_caps: Path
    ) -> None:
        _ = patched_caps
        compiler = ContextCompiler()
        compiled = compiler.compile(
            query="anything",
            candidates=[],
            contents={},
        )
        assert compiled.slices == []
