#!/usr/bin/env python3
"""Produce an evidence-bounded Qwen stock-MLX versus Pheno Metal matrix.

The runner executes stock MLX's full Qwen forward only when a compatible
``mlx_lm`` model is explicitly supplied.  It intentionally records Pheno as
``unsupported`` for end-to-end rows: the current real-weights Metal decode is
RMSNorm-only and does not execute the same Qwen workload.  Component validation
is retained as evidence, never converted into an end-to-end performance claim.

Examples::

    # Record all required variants and available Pheno validation evidence.
    python3 python/qwen_comparison_matrix.py --out-dir bench/results/qwen-comparison

    # Also run stock MLX using a locally available mlx_lm model.
    python3 python/qwen_comparison_matrix.py --mlx-model /path/to/mlx-qwen \
        --out-dir bench/results/qwen-comparison
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
KERNEL_ROOT = HERE.parent
DEFAULT_VALIDATION_REPORT = KERNEL_ROOT / "bench" / "results" / "validate_latest.json"
DEFAULT_OUTPUT_DIR = KERNEL_ROOT / "bench" / "results" / "qwen-comparison"
DEFAULT_BATCHES = [1, 8]
DEFAULT_CONTEXTS = [1, 128]

PHENO_COMPARISON_CAVEAT = (
    "Pheno Metal is not an end-to-end Qwen comparator: the available real-"
    "weights decode runs RMSNorm only; attention, MLP, and projection kernels "
    "are not wired into that decode path."
)


def _system_info() -> dict[str, str]:
    try:
        import mlx.core as mx

        mlx_version = getattr(mx, "__version__", "unknown")
    except ImportError:
        mlx_version = "unavailable"
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "mlx_version": mlx_version,
    }


def build_variants(batches: list[int], contexts: list[int]) -> list[dict[str, Any]]:
    """Return the requested full-forward comparison grid.

    The schema makes the non-comparability decision explicit rather than
    leaving consumers to infer performance from unrelated component timings.
    """
    return [
        {
            "batch": batch,
            "context_tokens": context,
            "workload": "full_qwen_forward_logits",
            "comparison_status": "not_comparable",
            "pheno_metal": {
                "execution_status": "unsupported",
                "reason": PHENO_COMPARISON_CAVEAT,
                "metrics": None,
            },
        }
        for batch in batches
        for context in contexts
    ]


def load_pheno_validation_evidence(report_path: Path) -> dict[str, Any]:
    """Load component validation without labelling it as an e2e comparison."""
    evidence: dict[str, Any] = {
        "report_path": str(report_path),
        "comparison_caveat": PHENO_COMPARISON_CAVEAT,
        "component_results": [],
    }
    if not report_path.is_file():
        return evidence | {"report_status": "not_found", "metal_available": None}

    try:
        raw = json.loads(report_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return evidence | {
            "report_status": "unreadable",
            "metal_available": None,
            "error": f"{type(exc).__name__}: {exc}",
        }

    component_results = []
    for row in raw.get("results", []):
        component_results.append(
            {
                key: row.get(key)
                for key in (
                    "name",
                    "passed",
                    "metal_available",
                    "mlx_ms",
                    "metal_ms",
                    "max_abs_diff_metal",
                    "notes",
                )
            }
        )
    return evidence | {
        "report_status": "loaded",
        "metal_available": raw.get("metal_available"),
        "component_results": component_results,
    }


def _stock_mlx_worker(
    model: str, batch: int, context: int, iters: int, warmup: int
) -> str:
    """Return a subprocess program so each MLX variant gets a fresh process."""
    return f"""\
import json
import time
import mlx.core as mx
from mlx_lm import load

model, tokenizer = load({model!r})
ids = mx.zeros(({batch}, {context}), dtype=mx.int32)

def run():
    logits = model(ids)
    mx.eval(logits)
    return logits

for _ in range({warmup}):
    run()
mx.synchronize()
t0 = time.perf_counter()
for _ in range({iters}):
    out = run()
mx.synchronize()
elapsed = time.perf_counter() - t0
shape = list(out.shape)
print(json.dumps({{
    "execution_status": "completed",
    "ms_per_forward": elapsed * 1000 / {iters},
    "tokens_per_sec": {batch * context} / (elapsed / {iters}),
    "shape": shape,
    "finite": bool(mx.all(mx.isfinite(out)).item()),
}}))
"""


def run_stock_mlx_variant(
    model: str | None,
    batch: int,
    context: int,
    iters: int,
    warmup: int,
) -> dict[str, Any]:
    """Run one stock-MLX full-forward row or return an auditable skip."""
    base = {"batch": batch, "context_tokens": context}
    if not model:
        return base | {
            "execution_status": "skipped",
            "reason": "--mlx-model was not supplied; stock MLX workload was not run",
        }
    if importlib.util.find_spec("mlx_lm") is None:
        return base | {
            "execution_status": "skipped",
            "reason": "mlx_lm is not installed; stock MLX workload was not run",
        }
    if not Path(model).exists() and "/" in model:
        return base | {
            "execution_status": "skipped",
            "reason": f"stock MLX model path does not exist: {model}",
        }

    command = [
        sys.executable,
        "-c",
        _stock_mlx_worker(model, batch, context, iters, warmup),
    ]
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            command, capture_output=True, text=True, timeout=180, check=False
        )
    except subprocess.TimeoutExpired:
        return base | {
            "execution_status": "failed",
            "reason": "stock MLX worker timed out after 180s",
        }

    result = base | {
        "worker_command": [sys.executable, "-c", "<embedded stock-MLX worker>"],
        "elapsed_wall_ms": (time.perf_counter() - started) * 1000,
    }
    if proc.returncode != 0:
        return result | {
            "execution_status": "failed",
            "reason": f"stock MLX worker exited {proc.returncode}",
            "stderr_tail": "\n".join(proc.stderr.splitlines()[-10:]),
        }
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        return result | {
            "execution_status": "failed",
            "reason": f"stock MLX worker produced no parseable JSON: {type(exc).__name__}",
            "stdout_tail": "\n".join(proc.stdout.splitlines()[-10:]),
        }
    return result | payload


def make_report(
    *,
    variants: list[dict[str, Any]],
    mlx_rows: list[dict[str, Any]],
    evidence: dict[str, Any],
    methodology: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the stable, machine-readable report schema."""
    mlx_by_variant = {(row["batch"], row["context_tokens"]): row for row in mlx_rows}
    rows = []
    for variant in variants:
        row = dict(variant)
        row["stock_mlx"] = mlx_by_variant[(row["batch"], row["context_tokens"])]
        rows.append(row)
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "system": _system_info(),
        "methodology": methodology,
        "comparison_policy": {
            "end_to_end_metric_policy": "Only same-workload measurements are comparable.",
            "pheno_metal_caveat": PHENO_COMPARISON_CAVEAT,
            "unsupported_claims": [
                "No Pheno-versus-stock-MLX end-to-end latency, throughput, or speedup is calculated.",
                "Component validation timings are not substituted for full-model performance.",
            ],
        },
        "rows": rows,
        "pheno_validation_evidence": evidence,
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render the companion human-readable matrix from the JSON report."""
    method = report["methodology"]
    lines = [
        "# Qwen Stock MLX vs Pheno Metal Comparison Matrix",
        "",
        "## Scope and interpretation",
        "",
        f"- {report['comparison_policy']['pheno_metal_caveat']}",
        "- Rows are marked **not comparable** until both sides execute the same full Qwen workload.",
        "- Component validation evidence below is retained for correctness and implementation tracking only.",
        "",
        "## Methodology",
        "",
        f"- Workload: `{method['workload']}`",
        f"- Stock MLX source: `{method['stock_mlx_source']}`",
        f"- Batches: `{method['batches']}`; context tokens: `{method['contexts']}`",
        f"- Timed iterations: `{method['iters']}`; warmups: `{method['warmup']}`",
        f"- Weights: {method['weights']}",
        f"- Timing boundary: {method['timing_boundary']}",
        "",
        "## Full-workload matrix",
        "",
        "| Batch | Context | Stock MLX | Pheno Metal | Comparison |",
        "| ---: | ---: | --- | --- | --- |",
    ]
    for row in report["rows"]:
        mlx = row["stock_mlx"]
        mlx_status = mlx["execution_status"]
        if mlx_status == "completed":
            mlx_text = f"completed; {mlx['ms_per_forward']:.2f} ms/fwd; {mlx['tokens_per_sec']:.1f} tok/s"
        else:
            mlx_text = f"{mlx_status}; {mlx.get('reason', 'no result')}"
        lines.append(
            f"| {row['batch']} | {row['context_tokens']} | {mlx_text} | "
            f"{row['pheno_metal']['execution_status']} | not comparable |"
        )

    evidence = report["pheno_validation_evidence"]
    lines += [
        "",
        "## Pheno component-validation evidence (not an end-to-end comparison)",
        "",
        f"- Report: `{evidence['report_path']}` ({evidence['report_status']})",
        f"- Metal available when report was written: `{evidence['metal_available']}`",
        "",
        "| Component | Passed | Metal available | MLX ms | Metal ms | Notes |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    if evidence["component_results"]:
        for item in evidence["component_results"]:
            lines.append(
                f"| {item['name']} | {item['passed']} | {item['metal_available']} | "
                f"{item['mlx_ms']} | {item['metal_ms']} | {item['notes'] or ''} |"
            )
    else:
        lines.append("| No validation rows available | — | — | — | — | — |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--mlx-model",
        help="Local path or mlx_lm model identifier for stock-MLX execution",
    )
    parser.add_argument("--batches", type=int, nargs="+", default=DEFAULT_BATCHES)
    parser.add_argument("--contexts", type=int, nargs="+", default=DEFAULT_CONTEXTS)
    parser.add_argument("--iters", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument(
        "--validation-report", type=Path, default=DEFAULT_VALIDATION_REPORT
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    if (
        any(value < 1 for value in args.batches + args.contexts)
        or args.iters < 1
        or args.warmup < 0
    ):
        parser.error(
            "batches, contexts, and iters must be positive; warmup must be non-negative"
        )

    variants = build_variants(args.batches, args.contexts)
    mlx_rows = [
        run_stock_mlx_variant(
            args.mlx_model, row["batch"], row["context_tokens"], args.iters, args.warmup
        )
        for row in variants
    ]
    methodology = {
        "workload": "full Qwen logits forward [batch, context] -> [batch, context, vocab]",
        "stock_mlx_source": "mlx_lm model forward in an isolated subprocess per variant",
        "weights": "the supplied mlx_lm model; no synthetic-weight timings are used for stock-MLX rows",
        "batches": args.batches,
        "contexts": args.contexts,
        "iters": args.iters,
        "warmup": args.warmup,
        "timing_boundary": "wall clock around evaluated forwards after warmup, followed by mx.synchronize()",
        "pheno_metal_workload": "not run: current real-weights implementation is RMSNorm-only decode",
        "environment_overrides": {
            key: os.environ[key]
            for key in ("QWEN35_HF_DIR", "PHENO_DYLIB_PATH", "PHENO_METAL_LIB")
            if key in os.environ
        },
    }
    report = make_report(
        variants=variants,
        mlx_rows=mlx_rows,
        evidence=load_pheno_validation_evidence(args.validation_report),
        methodology=methodology,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "qwen_stock_mlx_vs_pheno_metal.json"
    markdown_path = args.out_dir / "qwen_stock_mlx_vs_pheno_metal.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    markdown_path.write_text(render_markdown(report))

    completed = sum(
        row["stock_mlx"]["execution_status"] == "completed" for row in report["rows"]
    )
    print(f"Wrote machine-readable matrix: {json_path}")
    print(f"Wrote human-readable matrix: {markdown_path}")
    print(f"Stock MLX rows completed: {completed}/{len(report['rows'])}")
    print(
        "Pheno rows are intentionally not comparable; see methodology and validation evidence."
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
