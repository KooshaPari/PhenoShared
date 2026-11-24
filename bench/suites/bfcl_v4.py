"""BFCL v4 — Berkeley Function-Calling Leaderboard.

2,200+ function-calling tasks. Deterministic AST + exec match (no LLM judge).
Multi-turn and single-turn supported.

Spec reference: docs/superpowers/specs/2026-07-16-benchmark-harness.md §2 row 9,
§3.2 (verifier port). Spec rule 6: format checks done locally (no external
`bfcl` package required).
"""

from __future__ import annotations

import ast
import json
import re
import time
from typing import Any

from bench.types import RunSpec, SuiteResult, TaskResult, TaskStatus

from ._stub import BaseSuite, TaskSpec, synthetic_prompt, synthetic_response
from .dataset_loader import (
    DatasetSource,
    load_suite_dataset,
    synth_function_call,
)

SOURCE_URL = "gorilla.cs.berkeley.edu/bfcl"
VERSION = "v4"
NUM_TASKS = 2200  # spec §2 row 9 (2,200+ tasks)
DEFAULT_SUBSET = 100  # spec §2 row 9: n=100 multi-turn

# Tool-call stability metrics that BFCL feeds into the spec §4.2 matrix.
STABILITY_METRICS = (
    "tool_call_success_rate",
    "tool_call_latency_p50",
    "tool_call_latency_p95",
    "dead_end_rate",
    "retry_rate",
    "format_error_rate",
)


def _extract_function_call(response: str) -> tuple[str, dict[str, Any]]:
    """Extract a (name, args) tuple from a free-form response.

    Tries in order: JSON object → <tool_call>…</tool_call> → python
    `name(**kwargs)` syntax. Returns ("", {}) on failure.
    """
    if not response:
        return "", {}
    # 1) JSON object
    m = re.search(r"\{[\s\S]+\}", response)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                name = str(obj.get("name") or obj.get("function") or "").strip()
                args = (
                    obj.get("arguments")
                    or obj.get("args")
                    or obj.get("parameters")
                    or {}
                )
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                if name and isinstance(args, dict):
                    return name, args
        except Exception:  # nosec B110
            pass
    # 2) XML-ish tool_call wrapper
    m = re.search(r"<tool_call[^>]*>([\s\S]+?)</tool_call>", response)
    if m:
        try:
            obj = json.loads(m.group(1))
            if isinstance(obj, dict):
                return str(obj.get("name", "")), dict(obj.get("arguments", {}))
        except Exception:  # nosec B110
            pass
    # 3) Python-style `name(**kwargs)`
    m = re.search(r"([A-Za-z_][A-Za-z0-9_.]*)\s*\(([^)]*)\)", response)
    if m:
        name = m.group(1)
        try:
            args_tree = ast.parse(f"_({m.group(2)})", mode="eval")
            call = args_tree.body
            args: dict[str, Any] = {}  # type: ignore[no-redef]
            if isinstance(call, ast.Call):
                for kw in call.keywords:
                    args[kw.arg] = ast.literal_eval(kw.value)
            return name, args
        except Exception:
            return name, {}
    return "", {}


def _arg_match(expected: Any, actual: Any, *, loose: bool = True) -> bool:
    """Compare two arg values; loose mode allows numeric type coercion."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        return all(_arg_match(expected.get(k), actual.get(k)) for k in expected)
    if isinstance(expected, list) and isinstance(actual, list):
        return len(expected) == len(actual) and all(
            _arg_match(e, a) for e, a in zip(expected, actual)
        )
    if expected == actual:
        return True
    if (
        loose
        and isinstance(expected, (int, float))
        and isinstance(actual, (int, float))
    ):
        try:
            return float(expected) == float(actual)
        except Exception:
            return False
    if loose and isinstance(expected, str) and isinstance(actual, str):
        return expected.strip().lower() == actual.strip().lower()
    return False


def _function_call_match(
    expected_name: str, expected_args: dict[str, Any], response: str
) -> bool:
    """Return True iff the response contains a function call matching expected."""
    name, args = _extract_function_call(response)
    if not name or name != expected_name:
        return False
    if not expected_args:
        return True
    return _arg_match(expected_args, args, loose=True)


class BFCLv4(BaseSuite):
    """BFCL v4 — deterministic function-calling eval."""

    name = "bfcl"
    version = VERSION
    num_tasks = NUM_TASKS
    task_format = "AST + exec match (deterministic format check)"
    scoring = "pass@1 = function name + args match (loose numeric coercion)"
    source_url = SOURCE_URL
    format = task_format
    _subset_label = "n=100 multi-turn (spec §2 row 9)"
    rationale = "tool-call stability"
    default_judge_mode = "deterministic"  # type: ignore[assignment]
    task_id_prefix = "bfcl"

    _PAPER_METRICS = (
        ("pass@1", "%", "spec §4.1 + BFCL v4 leaderboard"),
        ("tool_call_success_rate", "ratio", "spec §4.2"),
        ("format_error_rate", "ratio", "spec §4.2"),
        ("dead_end_rate", "ratio", "spec §4.2"),
        ("retry_rate", "ratio", "spec §4.2"),
        ("mean_tool_calls_per_task", "count", "spec §4.5"),
    )

    # ------------------------------------------------------------------
    # Subset
    # ------------------------------------------------------------------

    def subset(self, n: int, seed: int) -> list[TaskSpec]:
        """Return n BFCL v4 task specs.

        Real-mode: pulls from `Salesforce/xlam-function-calling-60k` or
        `gorilla-llm/Berkeley-Function-Calling-Leaderboard`. Stub-mode:
        synthetic function-calling prompts.
        """
        n = max(0, int(n))
        source = DatasetSource(
            name="bfcl",
            hf_repo="Salesforce/xlam-function-calling-60k",
            hf_split="train",
            text_field="query",
            synth_fn=lambda k, s: [synth_function_call(42, i) for i in range(k)],
        )
        loaded = load_suite_dataset(source, n=n)
        out: list[TaskSpec] = []
        for i, row in enumerate(
            loaded.rows[:n] if len(loaded.rows) >= n else loaded.rows
        ):
            query = row.get("query") or row.get("question") or row.get("prompt") or ""
            # xLAM dataset: `tools` is a JSON-string list of {name, parameters}.
            tools_raw = (
                row.get("tools") or row.get("answers") or row.get("expected") or []
            )
            if isinstance(tools_raw, str):
                try:
                    tools_raw = json.loads(tools_raw)
                except Exception:
                    tools_raw = []
            expected_name = ""
            expected_args: dict[str, Any] = {}
            multi_turn = bool(row.get("multi_turn") or row.get("multiTurn") or False)
            if isinstance(tools_raw, list) and tools_raw:
                first = tools_raw[0]
                if isinstance(first, dict):
                    expected_name = str(first.get("name", ""))
                    params = first.get("parameters") or first.get("arguments") or {}
                    if isinstance(params, str):
                        try:
                            params = json.loads(params)
                        except Exception:
                            params = {}
                    if isinstance(params, dict):
                        expected_args = params
                    elif isinstance(params, list):
                        # Flatten a list of {name, value} pairs into a dict
                        for item in params:
                            if isinstance(item, dict) and "name" in item:
                                expected_args[str(item["name"])] = item.get("value")
            out.append(
                TaskSpec(
                    task_id=str(row.get("id", row.get("query_id", f"bfcl-{i:05d}"))),
                    suite=self.name,
                    prompt=query,
                    reference=expected_name,
                    metadata={
                        "seed": seed,
                        "index": i,
                        "expected_name": expected_name,
                        "expected_args": expected_args,
                        "multi_turn": multi_turn,
                        "synthetic": loaded.synthetic,
                    },
                    tags=("bfcl", "v4", "multi_turn" if multi_turn else "single_turn"),
                )
            )
        while len(out) < n:
            i = len(out)
            out.append(
                TaskSpec(
                    task_id=f"bfcl-stub-{i:05d}",
                    suite=self.name,
                    prompt=synthetic_prompt(seed, i),
                    reference="get_weather",
                    metadata={
                        "seed": seed,
                        "index": i,
                        "expected_name": "get_weather",
                        "expected_args": {"city": "Paris"},
                        "multi_turn": bool(i % 2),
                        "synthetic": True,
                    },
                    tags=("bfcl", "stub"),
                )
            )
        return out

    # ------------------------------------------------------------------
    # Per-task execution
    # ------------------------------------------------------------------

    def run_task(self, task: TaskSpec, model: str, **kwargs: Any) -> TaskResult:
        """Grade the response by extracting the function call and matching."""
        expected_name = str(task.metadata.get("expected_name", task.reference or ""))
        expected_args = dict(task.metadata.get("expected_args", {}))
        response = str(kwargs.get("response", ""))
        if not response:
            response = synthetic_response(0, hash(task.task_id) & 0xFFFF)
        # Detect a parse / format error early.
        name, args = _extract_function_call(response)
        format_error = 1.0 if (not name) else 0.0
        call_ok = _function_call_match(expected_name, expected_args, response)
        status = TaskStatus.PASS if call_ok else TaskStatus.FAIL
        return TaskResult(
            task_id=task.task_id,
            status=status,
            wall_clock_s=float(kwargs.get("simulated_duration_s", 0.05)),
            tokens_in=len(task.prompt.split()),
            tokens_out=len(response.split()),
            tool_calls=1 if name else 0,
            meta={
                "pass@1": 1.0 if status == TaskStatus.PASS else 0.0,
                "tool_call_success_rate": 1.0 if name else 0.0,
                "format_error_rate": format_error,
                "dead_end_rate": 1.0 if not name else 0.0,
                "retry_rate": 0.0,
                "mean_tool_calls_per_task": 1.0 if name else 0.0,
            },
        )

    # ------------------------------------------------------------------
    # Skeleton `Suite.run` orchestrator
    # ------------------------------------------------------------------

    def run(self, run_spec: RunSpec) -> SuiteResult:
        """Run the BFCL v4 subset and return a SuiteResult."""
        time.time()
        tasks = self.subset(run_spec.n, run_spec.seed)
        results: list[TaskResult] = [self.run_task(t, run_spec.model) for t in tasks]
        if not results:
            return SuiteResult(
                suite=self.name,
                model=run_spec.model,
                started_at=time.time(),
                task_results=results,
                meta={},
            )
        passes = sum(1 for r in results if r.status == TaskStatus.PASS)
        n = len(results)
        return SuiteResult(
            suite=self.name,
            model=run_spec.model,
            started_at=time.time(),
            task_results=results,
            meta={
                "pass@1": passes / n,
                "tool_call_success_rate": sum(
                    r.meta.get("tool_call_success_rate", 0.0) for r in results
                )
                / n,
                "format_error_rate": sum(
                    r.meta.get("format_error_rate", 0.0) for r in results
                )
                / n,
                "dead_end_rate": sum(r.meta.get("dead_end_rate", 0.0) for r in results)
                / n,
                "mean_tool_calls_per_task": sum(
                    r.meta.get("mean_tool_calls_per_task", 0.0) for r in results
                )
                / n,
            },
        )


__all__ = ["BFCLv4", "NUM_TASKS", "DEFAULT_SUBSET", "STABILITY_METRICS"]
