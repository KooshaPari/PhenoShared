#!/usr/bin/env python3
"""5-minute energy baseline: single-cell (1 task x 1 variant) with energy measurement.

Usage:
    python scripts/run_energy_baseline.py --model Qwen3.5-0.8B --backend mock --tasks deepswe
"""

from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bench.energy import make_source
from bench.energy_schema import EnergyResult
from bench.types import EnergySource


def _get_peak_rss_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_maxrss / 1024.0


def run_single_cell(
    model: str,
    backend: str,
    suite_name: str,
    energy_source: EnergySource,
) -> EnergyResult:
    from bench.adapters import build_adapter
    from bench.executor import iter_task_descriptors
    from bench.registry import get_suite
    from bench.types import RunSpec

    spec = RunSpec(
        suite=suite_name,
        n=1,
        seed=0,
        model=model,
        energy_source=energy_source,
        output="",
    )

    adapter = build_adapter(model)
    suite_cls = get_suite(suite_name)
    suite_cls()

    source = make_source(energy_source)
    source.start()
    rss_before = _get_peak_rss_mb()

    started = time.monotonic()
    tasks = list(iter_task_descriptors(spec))
    td = tasks[0] if tasks else None

    tokens_out = 0
    latency_ms = 0.0

    if td is not None:
        messages = [{"role": "user", "content": td.prompt}]
        resp = adapter.generate(messages)
        getattr(resp, "text", "") or ""
        int(getattr(resp, "prompt_tokens", 0) or 0)
        tokens_out = int(getattr(resp, "completion_tokens", 0) or 0)
        latency_ms = float(getattr(resp, "latency_ms", 0.0) or 0.0)

    elapsed = time.monotonic() - started
    energy_total = source.stop()
    peak_rss = max(_get_peak_rss_mb(), rss_before)

    tokens_per_sec = tokens_out / elapsed if elapsed > 0 else 0.0
    energy_mj = energy_total.joules * 1000.0
    energy_per_token = energy_mj / tokens_out if tokens_out > 0 else 0.0

    try:
        adapter.aclose() if hasattr(adapter, "aclose") else None
    except Exception:
        pass

    return EnergyResult(
        model=model,
        backend=backend,
        suite=suite_name,
        task_id=td.task_id if td else "none",
        latency_ms=latency_ms,
        tokens_per_sec=tokens_per_sec,
        energy_mj=energy_mj,
        energy_per_token_mj=energy_per_token,
        peak_rss_mb=peak_rss,
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Energy baseline: single cell measurement")
    p.add_argument("--model", required=True, help="Model name")
    p.add_argument("--backend", default="mock", help="Backend/adapter name")
    p.add_argument("--tasks", required=True, help="Comma-separated suite names")
    p.add_argument(
        "--energy-source",
        choices=["none", "m1_pmu", "nvidia_smi", "powermetrics"],
        default="powermetrics",
    )
    args = p.parse_args()

    suite_names = [s.strip() for s in args.tasks.split(",") if s.strip()]
    energy_source = EnergySource(args.energy_source)

    results: list[dict] = []
    for suite_name in suite_names:
        print(
            f"[energy-baseline] suite={suite_name} model={args.model} source={energy_source.value}",
            flush=True,
        )
        try:
            result = run_single_cell(
                args.model, args.backend, suite_name, energy_source
            )
            results.append(result.to_dict())
            print(
                f"  latency={result.latency_ms:.1f}ms  tok/s={result.tokens_per_sec:.1f}  "
                f"energy={result.energy_mj:.1f}mJ  mJ/tok={result.energy_per_token_mj:.3f}  "
                f"RSS={result.peak_rss_mb:.0f}MB",
                flush=True,
            )
        except Exception as e:
            print(f"  ERROR: {e}", flush=True)
            results.append({"suite": suite_name, "error": str(e)})

    out_dir = Path("bench/results/energy-baseline")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out_file = out_dir / f"baseline_{ts}.json"
    out_file.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\nResults written to {out_file}")


if __name__ == "__main__":
    main()
