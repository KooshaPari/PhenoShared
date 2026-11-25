"""bench.eval_runner — Wire the eval harness to run LLM benchmarks via adapters.

Provides ``EvalRunner``, a class that takes a suite config (prompts +
expected outputs), selects an adapter (Anthropic, OpenAI, MLX, Mock),
runs prompts through the adapter, collects timing / token / verdict
metrics, and writes structured JSONL output.

Plugin hooks used:
    pre_metric  / post_metric  — wall-clock timing around each task
    post_judge                 — telemetry counts per verdict
    pre_judge                  — normalize the response text before judging

CLI entry point:
    python -m bench.eval_runner --suite <name> --adapter <adapter>

Example:
    python -m bench.eval_runner --suite arithmetic --adapter mock
    python -m bench.eval_runner --suite arithmetic --adapter openai \\
        --adapter-opts '{"model":"gpt-4o-mini","api_key":"sk-..."}'
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bench.adapters import ModelAdapter, ModelResponse, make_adapter
from bench.plugin import PluginRegistry, default_registry

# ---------------------------------------------------------------------------
# Suite config
# ---------------------------------------------------------------------------


@dataclass
class EvalTask:
    """A single benchmark task: prompt + expected output."""

    task_id: str
    prompt: str
    expected: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalSuiteConfig:
    """Suite configuration: name + list of tasks."""

    name: str
    tasks: list[EvalTask] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EvalSuiteConfig:
        """Build from a JSON-friendly dict (e.g. loaded from a file)."""
        tasks = [
            EvalTask(
                task_id=t["task_id"],
                prompt=t["prompt"],
                expected=t.get("expected", ""),
                metadata=t.get("metadata", {}),
            )
            for t in d.get("tasks", [])
        ]
        return cls(name=d.get("name", "unnamed"), tasks=tasks)

    @classmethod
    def from_json_file(cls, path: str | Path) -> EvalSuiteConfig:
        """Load a suite config from a JSON file."""
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(raw)


# ---------------------------------------------------------------------------
# Verdict (simple exact / contains match)
# ---------------------------------------------------------------------------


def _default_verdict(response_text: str, expected: str) -> str:
    """Deterministic verdict: 'pass' if expected is a substring, else 'fail'.

    Returns 'skip' when expected is empty (informational tasks).
    """
    if not expected:
        return "skip"
    if expected.strip().lower() in response_text.strip().lower():
        return "pass"
    return "fail"


# ---------------------------------------------------------------------------
# EvalResult
# ---------------------------------------------------------------------------


@dataclass
class EvalResult:
    """Result for one task execution."""

    task_id: str
    prompt: str
    response: str
    expected: str
    verdict: str  # "pass" | "fail" | "skip" | "error"
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    wall_clock_sec: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "prompt": self.prompt,
            "response": self.response,
            "expected": self.expected,
            "verdict": self.verdict,
            "latency_ms": self.latency_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "wall_clock_sec": self.wall_clock_sec,
            "error": self.error,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# EvalRunner
# ---------------------------------------------------------------------------


class EvalRunner:
    """Run an eval suite through an adapter, collect metrics, emit JSONL.

    Parameters
    ----------
    suite_config : EvalSuiteConfig
        Prompts and expected outputs.
    adapter : ModelAdapter
        Any object satisfying the ``ModelAdapter`` protocol (Mock, OpenAI,
        Anthropic, MLX, etc.).
    registry : PluginRegistry | None
        Plugin registry for timing / telemetry hooks. Defaults to the
        process-wide built-in registry.
    verdict_fn : callable | None
        Override the default verdict function ``(response_text, expected) -> str``.
    """

    def __init__(
        self,
        suite_config: EvalSuiteConfig,
        adapter: ModelAdapter,
        *,
        registry: PluginRegistry | None = None,
        verdict_fn: Any = None,
    ) -> None:
        self.suite_config = suite_config
        self.adapter = adapter
        self.registry = registry or default_registry()
        self.verdict_fn = verdict_fn or _default_verdict
        self._results: list[EvalResult] = []

    # ---- public API -------------------------------------------------------

    def run(self) -> list[EvalResult]:
        """Execute all tasks and return results."""
        self._results.clear()

        # Plugin hook: pre_suite
        self.registry.dispatch(
            "pre_suite",
            self.suite_config.name,
            len(self.suite_config.tasks),
            0,
        )

        for task in self.suite_config.tasks:
            result = self._run_task(task)
            self._results.append(result)

        # Plugin hook: post_suite (tasks list for downstream plugins)
        self.registry.dispatch(
            "post_suite",
            self.suite_config.name,
            self._results,
        )

        return list(self._results)

    def run_task(self, task: EvalTask) -> EvalResult:
        """Run a single task (public entrypoint for granular use)."""
        return self._run_task(task)

    @property
    def results(self) -> list[EvalResult]:
        return list(self._results)

    def summary(self) -> dict[str, Any]:
        """Aggregate summary over completed results."""
        total = len(self._results)
        passed = sum(1 for r in self._results if r.verdict == "pass")
        failed = sum(1 for r in self._results if r.verdict == "fail")
        errored = sum(1 for r in self._results if r.verdict == "error")
        skipped = sum(1 for r in self._results if r.verdict == "skip")
        total_tokens_in = sum(r.prompt_tokens for r in self._results)
        total_tokens_out = sum(r.completion_tokens for r in self._results)
        latencies = [r.latency_ms for r in self._results if r.latency_ms > 0]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        return {
            "suite": self.suite_config.name,
            "adapter": self.adapter.name,
            "total": total,
            "passed": passed,
            "failed": failed,
            "errored": errored,
            "skipped": skipped,
            "pass_rate": passed / total if total else 0.0,
            "total_prompt_tokens": total_tokens_in,
            "total_completion_tokens": total_tokens_out,
            "avg_latency_ms": round(avg_latency, 2),
        }

    # ---- JSONL output -----------------------------------------------------

    def write_jsonl(self, path: str | Path) -> Path:
        """Write all results to a JSONL file.  Returns the resolved path."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            for result in self._results:
                f.write(json.dumps(result.to_dict(), default=str) + "\n")
        return p

    # ---- internals --------------------------------------------------------

    def _run_task(self, task: EvalTask) -> EvalResult:
        """Run a single task through the adapter with plugin hooks."""
        t_start = time.monotonic()

        # Plugin hook: pre_metric (timing plugin records start)
        self.registry.dispatch("pre_metric", task, _MetricsProxy())

        try:
            messages = [{"role": "user", "content": task.prompt}]
            response: ModelResponse = self.adapter.generate(messages)
        except Exception as exc:
            elapsed = time.monotonic() - t_start
            error_msg = f"{type(exc).__name__}: {exc}"
            self.registry.dispatch(
                "post_judge", task, _VerdictProxy("error")
            )
            return EvalResult(
                task_id=task.task_id,
                prompt=task.prompt,
                response="",
                expected=task.expected,
                verdict="error",
                latency_ms=elapsed * 1000,
                error=error_msg,
                metadata=dict(task.metadata),
            )

        elapsed = time.monotonic() - t_start
        raw_text = response.text

        # Plugin hook: pre_judge (normalization plugin may trim whitespace)
        pre_judge_results = self.registry.dispatch(
            "pre_judge", task, raw_text
        )
        judged_text = pre_judge_results[-1] if pre_judge_results else raw_text

        verdict = self.verdict_fn(judged_text, task.expected)

        result = EvalResult(
            task_id=task.task_id,
            prompt=task.prompt,
            response=raw_text,
            expected=task.expected,
            verdict=verdict,
            latency_ms=response.latency_ms,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            wall_clock_sec=elapsed,
            error=response.error,
            metadata=dict(task.metadata),
        )

        # Plugin hook: post_judge (telemetry plugin counts verdicts)
        self.registry.dispatch("post_judge", task, _VerdictProxy(verdict))

        # Plugin hook: post_metric (timing plugin records wall clock)
        metrics_proxy = _MetricsProxy()
        metrics_proxy.wall_clock_sec = elapsed
        self.registry.dispatch("post_metric", task, metrics_proxy)

        return result


# ---------------------------------------------------------------------------
# Lightweight proxies for plugin dispatch (avoids importing heavy types)
# ---------------------------------------------------------------------------


class _MetricsProxy:
    """Minimal stand-in so timing plugin can set wall_clock_sec."""

    def __init__(self) -> None:
        self.wall_clock_sec: float = 0.0


class _VerdictProxy:
    """Minimal stand-in so telemetry plugin can read .verdict."""

    def __init__(self, verdict: str) -> None:
        self.verdict = verdict


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bench.eval_runner",
        description="Run an eval suite against an LLM adapter and emit JSONL.",
    )
    p.add_argument(
        "--suite",
        required=True,
        help="Suite config JSON file path (or a registered suite name).",
    )
    p.add_argument(
        "--adapter",
        default="mock",
        help="Adapter name: mock | openai | anthropic | mlx (default: mock).",
    )
    p.add_argument(
        "--adapter-opts",
        default="{}",
        help='JSON string of adapter options, e.g. \'{"model":"gpt-4o-mini"}\'',
    )
    p.add_argument(
        "--output",
        default=None,
        help="Output JSONL path (default: bench/results/<suite>_<adapter>.jsonl).",
    )
    p.add_argument(
        "--no-plugins",
        action="store_true",
        help="Disable built-in plugins (timing, telemetry, normalize).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.  Returns 0 on success, 1 on error."""
    args = _build_parser().parse_args(argv)

    # --- load suite config ---
    suite_path = Path(args.suite)
    if suite_path.is_file():
        config = EvalSuiteConfig.from_json_file(suite_path)
    else:
        # Treat --suite as an inline name with empty tasks (smoke mode)
        config = EvalSuiteConfig(name=args.suite, tasks=[])

    # --- build adapter ---
    try:
        opts = json.loads(args.adapter_opts)
    except json.JSONDecodeError:
        print(f"error: invalid --adapter-opts JSON: {args.adapter_opts}", file=sys.stderr)
        return 1
    adapter = make_adapter(args.adapter, **opts)

    # --- optionally disable plugins ---
    registry: PluginRegistry | None = None
    if args.no_plugins:
        from bench.plugin import PluginRegistry as PR
        registry = PR()

    # --- output path ---
    output = args.output or f"bench/results/{config.name}_{adapter.name}.jsonl"

    # --- run ---
    runner = EvalRunner(config, adapter, registry=registry)
    results = runner.run()

    # --- write JSONL ---
    out_path = runner.write_jsonl(output)

    # --- summary ---
    summary = runner.summary()
    print(json.dumps(summary, indent=2))
    print(f"\nWrote {len(results)} results to {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
