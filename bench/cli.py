"""Top-level CLI for the pheno-harness benchmark suite (spec 2026-07-16).

.. deprecated::
    This bespoke CLI is deprecated as of 2026-07-21. The canonical CLI is
    ``portage/src/harbor/cli/main.py`` (Typer-based), invoked via the
    ``harbor`` command. Use ``harbor run --help`` for the canonical
    command surface; ``pheno-harness`` is smoke-test-only.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from bench import __version__
from bench.types import (
    EnergySource,
    JudgeMode,
    RunSpec,
    SuiteResult,
    TaskResult,
    TaskStatus,
)


def _ensure_suites_loaded() -> None:
    """Import side-effects: each suite module registers itself on import.

    Skeleton tests wipe the suite registry via an autouse fixture. Modules
    stay cached in ``sys.modules``, so we reload under overwrite mode when
    a known suite is missing.
    """
    import importlib
    import sys

    from bench.registry import allow_suite_overwrite, get_suite

    module_names = (
        "bench.suites.deepswe",
        "bench.suites.terminal_bench",
        "bench.suites.mmlu_pro",
        "bench.suites.gpqa_diamond",
        "bench.suites.hle",
        "bench.suites.mt_bench",
        "bench.suites.ifeval",
        "bench.suites.swe_bench_verified",
        "bench.suites.bfcl_v4",
        "bench.suites.perplexity",
    )
    try:
        get_suite("ifeval")
        return
    except KeyError:
        pass

    allow_suite_overwrite(True)
    try:
        for name in module_names:
            if name in sys.modules:
                importlib.reload(sys.modules[name])
            else:
                importlib.import_module(name)
    finally:
        allow_suite_overwrite(False)


def _self_test(args: argparse.Namespace) -> int:
    """JSON round-trip smoke against current TaskResult / SuiteResult shapes."""
    from bench.registry import registry_summary

    suite = getattr(args, "suite", None) or "self-test"
    model = getattr(args, "model", None) or "mock"
    print(f"[bench self-test] version={__version__}", flush=True)
    snap = registry_summary()
    print(
        f"[bench self-test] suites={len(snap['suites'])} tasks={len(snap['tasks'])} metrics={len(snap['metrics'])}",
        flush=True,
    )
    tasks = [
        TaskResult(
            task_id=f"self-test-{i}",
            status=TaskStatus.PASS if i % 2 == 0 else TaskStatus.FAIL,
            prompt=f"synthetic prompt {i}",
            completion=f"synthetic completion {i}",
            expected=None,
            meta={"pass_at_1": float(i % 2 == 0)},
            wall_clock_s=1.23 * (i + 1),
            tokens_in=10 * (i + 1),
            tokens_out=20 * (i + 1),
            cached=False,
        )
        for i in range(3)
    ]
    res = SuiteResult(
        suite=suite,
        model=model,
        run_id="self-test",
        started_at=0.0,
        stopped_at=4.0,
        tasks=tasks,
        passed=2,
        wrong=1,
        pass_at_1=2 / 3,
        meta={"notes": "synthetic"},
    )
    payload = res.to_json()
    parsed_obj = json.loads(payload)
    round_trip = SuiteResult.from_dict(parsed_obj)
    assert round_trip.suite == suite  # nosec B101
    assert round_trip.model == model  # nosec B101
    assert abs(round_trip.pass_at_1 - (2 / 3)) < 1e-9  # nosec B101
    assert round_trip.task_results[1].status == TaskStatus.FAIL  # nosec B101
    out = getattr(args, "self_test_output", None)
    if out:
        p = Path(out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(payload + "\n", encoding="utf-8")
        print(f"[bench self-test] wrote {p}", flush=True)
    print("[bench self-test] PASS", flush=True)
    return 0


def _list(_args: argparse.Namespace) -> int:
    _ensure_suites_loaded()
    from bench.registry import list_suites

    payload = {
        "version": __version__,
        "suite_count": len(list_suites()),
        "suites": [
            {"name": cls.name, "domain": getattr(cls, "domain", "?")}
            for cls in list_suites()
        ],
    }
    print(json.dumps(payload, sort_keys=True, indent=2))
    return 0


def _info(args: argparse.Namespace) -> int:
    _ensure_suites_loaded()
    from bench.registry import get_suite

    cls = get_suite(args.suite)
    payload = {
        "name": cls.name,
        "domain": getattr(cls, "domain", "?"),
        "module": cls.__module__,
        "doc": (cls.__doc__ or "").strip().splitlines()[0] if cls.__doc__ else "",
    }
    print(json.dumps(payload, sort_keys=True, indent=2))
    return 0


def _parse_spec(args: argparse.Namespace) -> RunSpec:
    return RunSpec(
        suite=args.suite,
        n=args.n,
        seed=args.seed,
        model=args.model,
        judge_model=args.judge_model,
        judge_mode=JudgeMode(args.judge_mode),
        energy_source=EnergySource(args.energy_source),
        output=args.output,
        run_id=args.run_id or f"run-{int(time.time())}",
    )


def _resolve_suite_alias(name: str) -> str:
    """Resolve a `--suite` alias to the registered suite name.

    Two sources are checked:

    1. If ``name`` is already a registered suite, return it unchanged.
    2. Otherwise look up ``bench.suites.SUITE_ALIASES`` which maps
       CLI-friendly aliases (``mock-fixture``) to their registered names
       (``ifeval``).

    Falls through unchanged if neither source resolves ``name``.
    """
    from bench.registry import get_suite
    from bench.suites import SUITE_ALIASES

    # Already a registered suite (e.g. ``ifeval``, ``mt-bench`` via the
    # alias table; or canonical ``ifeval`` itself).
    try:
        get_suite(name)
        return name
    except KeyError:
        pass

    # CLI-friendly alias (e.g. ``mock-fixture`` -> ``ifeval``).
    resolved = SUITE_ALIASES.get(name)
    if resolved is not None:
        return resolved

    return name


def _cmd_run_dry(args: argparse.Namespace) -> int:
    _ensure_suites_loaded()
    from bench.registry import get_suite

    spec = _parse_spec(args)
    spec.suite = _resolve_suite_alias(spec.suite)
    # Fail loud on unknown suites (same contract as `run`).
    get_suite(spec.suite)
    print(
        f"[bench dry-run] suite={spec.suite} n={spec.n} seed={spec.seed} "
        f"model={spec.model} judge_mode={spec.judge_mode.value} "
        f"energy_source={spec.energy_source.value}",
        flush=True,
    )
    spec_dict = spec.to_dict()
    print(json.dumps(spec_dict, sort_keys=True, indent=2))

    # If --output was explicitly specified, write a minimal EvaluationReport
    # envelope so consumers can verify the dry-run would have produced a valid
    # producer-side artifact (DAG-12 contract rule C6: artifact_kind is
    # the required fixed enum — see bench/contracts/EVAL_RESULT_CONTRACT.md).
    output_path = getattr(args, "output", None)
    if output_path:
        envelope: dict[str, Any] = {
            "contract_version": "0.5",
            "artifact_kind": "EvaluationReport",
            "run": {
                "run_id": spec.run_id,
                "variant": "ours",
                "model": spec.model,
                "judge_mode": spec.judge_mode.value,
                "energy_source": spec.energy_source.value,
                "evidence_label": "inferred",
            },
            "spec": spec_dict,
        }
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(envelope, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        # Envelope is written silently to --output so stdout stays a single
        # JSON object (the spec) for piping into jq / downstream consumers.
    return 0


def _build_messages(prompt: str) -> list[dict[str, Any]]:
    """Convert a single-prompt string into the OpenAI-style message list."""
    return [{"role": "user", "content": prompt}]


def _cmd_run(args: argparse.Namespace) -> int:
    _ensure_suites_loaded()
    from bench.adapters import build_adapter
    from bench.registry import get_suite

    spec = _parse_spec(args)
    adapter = build_adapter(spec.model)
    suite_cls = get_suite(spec.suite)
    suite_cls()
    print(
        f"[bench] running: suite={spec.suite} n={spec.n} seed={spec.seed} "
        f"model={spec.model} judge_mode={spec.judge_mode.value} "
        f"energy_source={spec.energy_source.value}",
        flush=True,
    )

    # Resolve tasks + iterate via the adapter (deterministic MockModel path).
    from bench.executor import iter_task_descriptors

    tasks = iter_task_descriptors(spec)
    started_at = time.monotonic()
    task_results: list[dict[str, Any]] = []
    passed = wrong = errored = 0
    total_in = total_out = 0
    for i, td in enumerate(tasks):
        messages = _build_messages(td.prompt)
        try:
            resp = adapter.generate(messages)
        except Exception as e:  # noqa: BLE001
            errored += 1
            task_results.append(
                {"task_id": td.task_id, "status": "ERROR", "error": str(e)}
            )
            continue
        text = getattr(resp, "text", "") or ""
        prompt_tokens = int(getattr(resp, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(resp, "completion_tokens", 0) or 0)
        latency_ms = float(getattr(resp, "latency_ms", 0.0) or 0.0)
        total_in += prompt_tokens
        total_out += completion_tokens
        is_pass = _verify(td, text)
        if is_pass:
            passed += 1
            status = "PASS"
        else:
            wrong += 1
            status = "FAIL"
        task_results.append(
            {
                "task_id": td.task_id,
                "status": status,
                "completion": text[:120],
                "latency_ms": float(latency_ms),
                "tokens_in": int(prompt_tokens),
                "tokens_out": int(completion_tokens),
            }
        )
        if (i + 1) % max(1, len(tasks) // 4) == 0 or i == len(tasks) - 1:
            print(
                f"  [{i + 1:>2}/{len(tasks)}] {status:4} {td.task_id:30s} "
                f"{latency_ms:6.1f}ms {prompt_tokens}→{completion_tokens} tok",
                flush=True,
            )
    stopped_at = time.monotonic()
    summary = {
        "run_id": spec.run_id,
        "suite": spec.suite,
        "model": spec.model,
        "n": len(tasks),
        "passed": passed,
        "wrong": wrong,
        "errored": errored,
        "pass_at_1": passed / len(tasks) if tasks else 0.0,
        "wall_clock_s": stopped_at - started_at,
        "tokens_in": total_in,
        "tokens_out": total_out,
        "tokens_per_s": total_out / (stopped_at - started_at)
        if stopped_at > started_at
        else 0.0,
    }
    print(json.dumps(summary, sort_keys=True, indent=2))
    # --output defaults to None from the parser; fall back to the legacy
    # "bench/results/run.json" path for the actual `run` sub-command so
    # historical callers that rely on a stable default artifact location
    # continue to work.
    output_target = args.output or "bench/results/run.json"
    if output_target:
        p = Path(output_target)
        p.parent.mkdir(parents=True, exist_ok=True)
        full = {
            **summary,
            "spec": spec.to_dict(),
            "task_results": task_results,
        }
        p.write_text(json.dumps(full, default=str, indent=2) + "\n")
        print(f"[bench] wrote {p}", flush=True)
    try:
        adapter.aclose() if hasattr(adapter, "aclose") else None
    except Exception:  # nosec B110
        pass
    return 0


def _verify(td: Any, text: str) -> bool:
    """Default verification: substring match against td.expected (if set)."""
    if td.expected is None:
        return True
    return str(td.expected).strip().lower() in (text or "").strip().lower()


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argparse parser (run / run-dry / list / info / self-test)."""

    p = argparse.ArgumentParser(
        prog="bench",
        description="Benchmark harness for pheno-harness (spec 2026-07-16-benchmark-harness).",
    )
    p.add_argument("--version", action="version", version=f"bench {__version__}")
    sub = p.add_subparsers(dest="command")

    def _add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--suite", required=True)
        sp.add_argument("--n", type=int, default=5)
        sp.add_argument("--seed", type=int, default=42)
        sp.add_argument("--model", default="Qwen3.5-0.8B")
        sp.add_argument("--judge-model", default="claude-sonnet-5")
        sp.add_argument(
            "--judge-mode",
            choices=[m.value for m in JudgeMode],
            default=JudgeMode.DETERMINISTIC.value,
        )
        sp.add_argument(
            "--energy-source",
            choices=[e.value for e in EnergySource],
            default=EnergySource.NONE.value,
        )
        # --output defaults to None so sub-command handlers can distinguish
        # "user explicitly chose a path" (write envelope there) from "no path
        # requested" (print only — default for dry-run introspection).
        sp.add_argument("--output", default=None)
        sp.add_argument("--run-id", default=None)

    run_p = sub.add_parser("run", help="Run a suite against a model adapter.")
    _add_common(run_p)
    run_p.set_defaults(func=_cmd_run)

    dry_p = sub.add_parser("run-dry", help="Echo resolved RunSpec without executing.")
    _add_common(dry_p)
    dry_p.set_defaults(func=_cmd_run_dry)

    list_p = sub.add_parser("list", help="List registered suites.")
    list_p.set_defaults(func=_list)

    info_p = sub.add_parser("info", help="Print details for a single suite.")
    info_p.add_argument("--suite", required=True)
    info_p.set_defaults(func=_info)

    self_p = sub.add_parser("self-test", help="Internal JSON round-trip smoke.")
    self_p.add_argument("--suite", default="self-test")
    self_p.add_argument("--model", default="mock")
    self_p.add_argument(
        "--self-test-output",
        default=None,
        help="Optional path to write SuiteResult JSON.",
    )
    self_p.set_defaults(func=_self_test)

    return p


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: dispatch to the chosen sub-command."""

    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "command", None) and getattr(args, "func", None) is not None:
        return int(args.func(args))
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
