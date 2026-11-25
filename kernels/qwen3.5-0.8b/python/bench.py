#!/usr/bin/env python3
"""
bench.py — Benchmark Qwen3.5 0.8B reference forward pass across sequence lengths.

What we measure:
  * ms / forward at each seq_len
  * tokens / sec (effective throughput)
  * Peak MLX working-set memory (via mx.metal.get_active_memory() when available)
  * End-to-end correctness (logits must be finite)

Sequence lengths: 1 (decode), 16 (small prompt), 128 (typical prompt),
512 (long prompt), 1024 (max single-shot prefill).  Larger seq_lens exceed
the practical Metal scratch budget for a single forward call and are
typically chunked in the production decoder.

Output:
  * JSON: bench/results/qwen3.5-0.8b-ref.json
  * stdout: per-row table sorted by seq_len

Usage::

    # Default sweep
    python3 python/bench.py

    # Custom seq_lens + more iters
    python3 python/bench.py --seq-lens 1 16 128 512 1024 --iters 10

    # Quick smoke
    python3 python/bench.py --quick

The reference is MLX; absolute numbers are **not** representative of the
hand-tuned Metal kernels — those live in `metal/` and are wired in by the
Metal agent.  This benchmark establishes the *gold standard* numbers we
need to match (or beat) once the Metal path lands.
"""

from __future__ import annotations

import argparse
import gc
import json
import platform
import sys
import time
from pathlib import Path

import mlx.core as mx

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from codegen import parse_arch_yaml  # noqa: E402
from reference import (  # noqa: E402
    ARCH,
    random_weights,
    ref_end_to_end_forward,
)

DEFAULT_SEQ_LENS = [1, 16, 128, 512, 1024]
DEFAULT_ITERS = 5
DEFAULT_WARMUP = 2


def _peak_mb() -> float | None:
    """Best-effort peak-MLX-memory read.

    MLX exposes ``mx.metal.get_active_memory()`` and ``mx.metal.get_peak_memory()``
    on Apple Silicon.  Fall back to ``mx.get_cache_memory()`` on other builds.
    Returns None when nothing is available.
    """
    try:
        if hasattr(mx.metal, "get_peak_memory"):
            return float(mx.metal.get_peak_memory()) / (1024 * 1024)
    except Exception:
        pass
    try:
        if hasattr(mx, "get_cache_memory"):
            return float(mx.get_cache_memory()) / (1024 * 1024)
    except Exception:
        pass
    return None


def _reset_peak() -> None:
    """Try to reset the peak-memory counter so each bench row is independent."""
    try:
        if hasattr(mx.metal, "reset_peak_memory"):
            mx.metal.reset_peak_memory()
    except Exception:
        pass


def _system_info() -> dict:
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "mlx_version": getattr(mx, "__version__", "unknown"),
        "is_apple_silicon": platform.machine() == "arm64" and sys.platform == "darwin",
    }


def _bench_one(seq_len: int, batch: int, iters: int, warmup: int, seed: int) -> dict:
    """Run one seq_len sweep entry; return dict with timings + peak mem."""
    mx.random.seed(seed)
    weights = random_weights(seed=seed)

    ids = mx.random.randint(0, ARCH.vocab_size, shape=(batch, seq_len)).astype(mx.int32)
    pos = mx.zeros((batch, seq_len, 3), dtype=mx.int32)
    # Sequential T positions, H/W at zero.
    for t in range(seq_len):
        pos = pos.at[:, t, 0].add(t)

    def _step():
        logits = ref_end_to_end_forward(ids, pos, weights)
        mx.eval(logits)
        return logits

    # Warmup (also triggers MLX graph compile + cache fills)
    for _ in range(warmup):
        out = _step()
    mx.synchronize() if hasattr(mx, "synchronize") else None
    _reset_peak()

    # Timed loop
    t0 = time.time()
    for _ in range(iters):
        out = _step()
    if hasattr(mx, "synchronize"):
        mx.synchronize()
    elapsed_s = time.time() - t0

    finite = bool(mx.all(mx.isfinite(out)).item())
    expected = (batch, seq_len, ARCH.vocab_size)
    shape_ok = tuple(out.shape) == expected
    peak = _peak_mb()

    avg_ms = (elapsed_s / iters) * 1000.0
    tokens = batch * seq_len
    tok_per_s = tokens / (elapsed_s / iters)

    return {
        "seq_len": seq_len,
        "batch": batch,
        "iters": iters,
        "warmup": warmup,
        "total_ms": elapsed_s * 1000.0,
        "ms_per_forward": avg_ms,
        "tokens_per_sec": tok_per_s,
        "tokens_per_iter": tokens,
        "peak_mlx_mb": peak,
        "shape_ok": shape_ok,
        "shape": list(out.shape),
        "finite": finite,
        "passed": shape_ok and finite,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--seq-lens",
        type=int,
        nargs="+",
        default=DEFAULT_SEQ_LENS,
        help="Sequence lengths to sweep (default: 1 16 128 512 1024)",
    )
    p.add_argument("--batch", type=int, default=1, help="Batch size")
    p.add_argument("--iters", type=int, default=DEFAULT_ITERS)
    p.add_argument("--warmup", type=int, default=DEFAULT_WARMUP)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="JSON output path (default: bench/results/qwen3.5-0.8b-ref.json)",
    )
    p.add_argument("--arch", type=Path, default=HERE.parent / "arch.yaml")
    p.add_argument(
        "--quick", action="store_true", help="Smoke benchmark: seq_lens=[1,16], iters=2"
    )
    args = p.parse_args(argv)

    if args.quick:
        args.seq_lens = [1, 16]
        args.iters = max(2, args.iters // 3)
        args.warmup = 1

    # Load arch (sanity check it parses; we use the Python ARCH constant for
    # runtime values, but a failed parse means the file is corrupt).
    arch = parse_arch_yaml(args.arch.read_text())
    print("Qwen3.5 0.8B reference benchmark (MLX)")
    print(
        f"  vocab={arch.vocab_size} hidden={arch.hidden_size} "
        f"layers={arch.num_hidden_layers}"
    )
    print(
        f"  full_attn_layers={arch.full_attention_num_layers} "
        f"lin_attn_layers={arch.linear_num_layers}"
    )
    print(f"  system: {_system_info()}")
    print(
        f"  seq_lens={args.seq_lens} batch={args.batch} "
        f"iters={args.iters} warmup={args.warmup}"
    )
    print()

    header = (
        f"{'STATUS':6} {'SEQ':>5} {'BATCH':>5} {'ms/FWD':>10} "
        f"{'tok/s':>9} {'peak_MB':>10}"
    )
    print(header)
    print("-" * len(header))

    rows: list[dict] = []
    n_pass = 0
    for s in args.seq_lens:
        gc.collect()
        try:
            row = _bench_one(s, args.batch, args.iters, args.warmup, args.seed)
        except Exception as e:
            row = {
                "seq_len": s,
                "batch": args.batch,
                "iters": args.iters,
                "warmup": args.warmup,
                "passed": False,
                "shape_ok": False,
                "finite": False,
                "error": repr(e),
            }
        rows.append(row)
        if row.get("passed"):
            n_pass += 1
        sym = "PASS" if row.get("passed") else "FAIL"
        ms = row.get("ms_per_forward")
        tps = row.get("tokens_per_sec")
        pm = row.get("peak_mlx_mb")
        print(
            f"  {sym:4} {row['seq_len']:>5} {row['batch']:>5} "
            f"{(f'{ms:.2f}' if ms else 'NA'):>10} "
            f"{(f'{tps:.1f}' if tps else 'NA'):>9} "
            f"{(f'{pm:.1f}' if pm else 'NA'):>10}"
            f"{('  ' + row['error']) if row.get('error') else ''}"
        )

    # Aggregate: best decode (S=1) tok/s, slowest (max-seq) ms.
    decode_row = next((r for r in rows if r["seq_len"] == 1), None)
    prefill_row = next((r for r in rows if r["seq_len"] == max(args.seq_lens)), None)

    summary = {
        "model_id": arch.model_id,
        "arch_yaml": str(args.arch),
        "system": _system_info(),
        "seq_lens": args.seq_lens,
        "batch": args.batch,
        "iters": args.iters,
        "warmup": args.warmup,
        "seed": args.seed,
        "results": rows,
        "summary": {
            "n_passed": n_pass,
            "n_total": len(rows),
            "decode_tok_per_sec": decode_row.get("tokens_per_sec")
            if decode_row
            else None,
            "max_seq_ms": prefill_row.get("ms_per_forward") if prefill_row else None,
        },
    }

    out_path = args.out or (HERE.parent / "bench" / "results" / "qwen3.5-0.8b-ref.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"\nWrote: {out_path}")

    if n_pass != len(rows):
        print(f"\n{n_pass}/{len(rows)} benchmarks passed.")
        return 1
    print(f"\nAll {n_pass}/{len(rows)} benchmarks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
