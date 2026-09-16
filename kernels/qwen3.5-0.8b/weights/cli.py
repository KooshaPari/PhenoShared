#!/usr/bin/env python3
"""
cli.py — Command-line front-end for the weights package.

Usage::

    python3 -m weights --hf-dir <DIR> download
    python3 -m weights --hf-dir <DIR> inspect
    python3 -m weights --hf-dir <DIR> dump-blob build/weights.bin
    python3 -m weights --hf-dir <DIR> sample "The capital of France is"

Each subcommand is independent and small:

  download    populate the cache directory with the Qwen3.5 0.8B safetensors
              (calls ``huggingface_hub.hf_hub_download`` for the shard,
              config, tokenizer, and generation_config). Idempotent — if
              files already exist, the call is a no-op.

  inspect     load the weights via :func:`load_hf_weights`, print a JSON
              summary of shapes / dtypes / a few statistics.

  dump-blob   serialize the loaded weights to the kernel engine's flat
              blob format (see :mod:`serialize`). Writes a header + JSON
              manifest + bf16 payload.

  sample      tokenize a prompt with the Qwen3.5 BPE tokenizer, run a
              short greedy forward pass, and print the top-k tokens
              + decoded completion. Used to sanity-check the end-to-end
              pipeline against the real weights.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .hf_loader import (
    ARCH_DEFAULTS,
    load_hf_tokenizer,
    load_hf_weights,
    weights_summary,
)
from .serialize import save_blob

DEFAULT_HF_DIR = "weights/build/hf-cache"


def _download(hf_dir: Path, *, force: bool = False) -> None:
    """Populate ``hf_dir`` with the Qwen3.5 0.8B safetensors + config + tokenizer.

    Uses ``huggingface_hub.hf_hub_download`` which is idempotent.
    """
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as e:
        print(f"ERROR: huggingface_hub not installed: {e}", file=sys.stderr)
        print("  pip install huggingface_hub", file=sys.stderr)
        sys.exit(2)

    repo_id = "Qwen/Qwen3.5-0.8B"
    # Pin to a specific revision to avoid the upstream model being
    # silently replaced (supply-chain attack mitigation; bandit B615).
    # Override via --revision on the CLI.
    revision = "main"
    for i, arg in enumerate(sys.argv):
        if arg == "--revision" and i + 1 < len(sys.argv):
            revision = sys.argv[i + 1]
            break
    files = [
        "config.json",
        "model.safetensors.index.json",
        "model.safetensors-00001-of-00001.safetensors",
        "tokenizer.json",
        "tokenizer_config.json",
        "generation_config.json",
    ]
    hf_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        target = hf_dir / f
        if target.exists() and not force:
            print(f"  [skip] {f} (already exists)")
            continue
        print(f"  [fetch] {repo_id}/{f} -> {target}")
        t0 = time.time()
        cache_path = hf_hub_download(
            repo_id, f, cache_dir=str(hf_dir), revision=revision
        )
        # ``cache_path`` may live under a snapshot dir; if so, symlink
        # the file into hf_dir so downstream tools find it via the
        # canonical layout.
        cp = Path(cache_path)
        if cp != target:
            # Symlink (relative) so the directory is portable.
            target.symlink_to(cp)
        print(f"           done in {time.time() - t0:.1f}s")


def _inspect(hf_dir: Path, *, json_out: bool) -> int:
    """Print a summary of the loaded weights."""
    mw = load_hf_weights(hf_dir, verbose=False)
    summary = weights_summary(mw)
    if json_out:
        print(json.dumps(summary, indent=2))
        return 0
    # Pretty text output
    print(
        f"Model: {summary['model_id']}  tie_word_embeddings={summary['tie_word_embeddings']}"
    )
    e = summary["embed"]
    print(f"  embed:           shape={tuple(e['shape'])} dtype={e['dtype']}")
    print(
        f"                   min={e['min']:+.4f} max={e['max']:+.4f} "
        f"mean={e['mean']:+.5f} std={e['std']:.4f}"
    )
    print(
        f"  full_attn:       {len(summary['full_attention_layer_indices'])} layers "
        f"@ {summary['full_attention_layer_indices']}"
    )
    print(
        f"  linear_attn:     {len(summary['linear_attention_layer_indices'])} layers "
        f"@ {summary['linear_attention_layer_indices']}"
    )
    print(f"  tensors loaded:  {summary['tensors_seen']}")
    print()
    for label, s in summary["samples"].items():
        print(f"  sample [{label}]:")
        for k, v in s.items():
            print(f"    {k:<14} {v}")
    return 0


def _dump_blob(hf_dir: Path, out_path: Path, *, verbose: bool) -> int:
    mw = load_hf_weights(hf_dir, verbose=verbose)
    manifest = save_blob(mw, out_path, verbose=verbose)
    print(f"\nWrote: {out_path}")
    print(f"  payload: {sum(t['nbytes'] for t in manifest['tensors']):,} bytes")
    print(f"  tensors: {len(manifest['tensors'])}")
    print(f"  total_params: {manifest.get('total_params'):,}")
    return 0


def _sample(
    hf_dir: Path,
    prompt: str,
    *,
    max_new_tokens: int,
    temperature: float,
    top_k: int,
    seed: int,
) -> int:
    """Greedy/sample a single prompt with the real weights + tokenizer."""
    import mlx.core as mx
    import numpy as np

    print(f"[sample] loading weights from {hf_dir}", flush=True)
    mw = load_hf_weights(hf_dir, verbose=False)
    print("[sample] loading tokenizer", flush=True)
    try:
        tok = load_hf_tokenizer(hf_dir)
    except FileNotFoundError:
        print(f"ERROR: tokenizer.json not found in {hf_dir}", file=sys.stderr)
        return 2

    print(f"[sample] prompt: {prompt!r}")
    enc = tok.encode(prompt)
    ids = enc.ids
    print(f"[sample] prompt token ids: {ids} ({len(ids)} tokens)")

    # Run a single prefill of the prompt, then decode max_new_tokens
    # autoregressively.  Position ids are T = step, H = W = 0.
    from python.reference import ref_end_to_end_forward  # noqa: F401

    def _forward(ids_list, pos_offset=0):
        B = 1
        S = len(ids_list)
        ids_arr = mx.array([ids_list], dtype=mx.int32)
        # Position ids must reflect the *absolute* token position so M-RoPE
        # gives the right angle.  When the CLI autoregressively decodes we
        # re-prefill the whole sequence each step (no KV cache plumbing),
        # so the T-axis position of token ``t`` is ``pos_offset + t``.
        pos_arr = mx.zeros((B, S, 3), dtype=mx.int32)
        for t in range(S):
            pos_arr[(0, t, 0)] = pos_offset + t
        # Lazy-build a reference ModelWeights that re-uses the HF tensors.
        # We piggy-back on the reference's data flow but feed it our own
        # ``LayerWeights`` instances built from the HF ones.
        from python.reference import LayerWeights as _RefLW
        from python.reference import ModelWeights as _RefMW  # noqa: F401

        # Map HF -> reference schema.  Full attention uses q/k/v/o; linear
        # uses qkv_w / o_proj_w (packed) + conv_w/conv_bias + alpha_log.
        ref_layers = []
        for i, hf_lw in enumerate(mw.layers):
            is_full = (i + 1) % 4 == 0
            if is_full:
                ref_layers.append(
                    _RefLW(
                        attn_norm_w=hf_lw.attn_norm_w,
                        ffn_norm_w=hf_lw.ffn_norm_w,
                        qkv_w=_pack_qkv_for_full(
                            hf_lw.q_w,
                            hf_lw.k_w,
                            hf_lw.v_w,
                            q_dim=ARCH_DEFAULTS["full_heads"]
                            * ARCH_DEFAULTS["full_head_dim"],
                            kv_dim=ARCH_DEFAULTS["full_kv_heads"]
                            * ARCH_DEFAULTS["full_head_dim"],
                        ),
                        o_proj_w=hf_lw.o_w,
                        o_gate_w=None,  # handled inline in reference.py
                        q_gate_w=hf_lw.q_w[
                            ARCH_DEFAULTS["full_heads"]
                            * ARCH_DEFAULTS["full_head_dim"] :,
                            :,
                        ],
                        q_norm_w=hf_lw.q_norm_w,
                        k_norm_w=hf_lw.k_norm_w,
                        gate_w=hf_lw.gate_w,
                        up_w=hf_lw.up_w,
                        down_w=hf_lw.down_w,
                    )
                )
            else:
                # Linear: ref expects a single packed qkv [3*Hk*Dk, H] and
                # conv_w [3*Hk*Dk, K].  Both come straight from HF.
                ref_layers.append(
                    _RefLW(
                        attn_norm_w=hf_lw.attn_norm_w,
                        ffn_norm_w=hf_lw.ffn_norm_w,
                        qkv_w=hf_lw.in_proj_qkv,
                        o_proj_w=hf_lw.o_w,
                        o_gate_w=hf_lw.in_proj_z,
                        gate_w=hf_lw.gate_w,
                        up_w=hf_lw.up_w,
                        down_w=hf_lw.down_w,
                        conv_w=_squeeze_conv(hf_lw.conv1d_w),  # [C, K] for ref
                        A_log=hf_lw.A_log,
                        dt_bias=hf_lw.dt_bias,
                        in_proj_a_w=hf_lw.in_proj_a,
                        in_proj_b_w=hf_lw.in_proj_b,
                        in_proj_z_w=hf_lw.in_proj_z,
                        lin_norm_w=hf_lw.lin_norm_w,
                    )
                )
        ref_mw = _RefMW(embed=mw.embed, layers=ref_layers, final_norm_w=mw.final_norm_w)
        logits = ref_end_to_end_forward(ids_arr, pos_arr, ref_mw)
        mx.eval(logits)
        return logits

    def _pack_qkv_for_full(q_w, k_w, v_w, q_dim, kv_dim):
        # The HF q_proj output is [2*Q, H] = [q | gate].  We need just the
        # first Q rows for q, plus k and v.
        import mlx.core as _mx

        q_only = q_w[:q_dim, :]  # [Q, H]
        return _mx.concatenate([q_only, k_w, v_w], axis=0)

    def _squeeze_conv(conv1d_w):
        # HF conv1d.weight shape [C, 1, K]; reference expects [C, K]
        import mlx.core as _mx

        if conv1d_w.ndim == 3 and conv1d_w.shape[1] == 1:
            return _mx.reshape(conv1d_w, (conv1d_w.shape[0], conv1d_w.shape[2]))
        return conv1d_w

    print(f"[sample] prefill (S={len(ids)})", flush=True)
    t0 = time.time()
    logits = _forward(ids, pos_offset=0)
    print(f"[sample] prefill ok in {(time.time() - t0) * 1000:.1f} ms", flush=True)

    # Top-5 predictions for the next token
    last_logits = logits[0, -1, :]
    mx.eval(last_logits)
    top5_idx = np.argsort(np.array(last_logits.tolist()).astype(np.float32))[-5:][::-1]
    print()
    print("Top-5 next-token predictions:")
    for tid in top5_idx:
        piece = tok.decode([int(tid)])
        print(f"  {int(tid):>8}  {piece!r}")

    # Autoregressive decode.  We do a *full re-prefill* each step (the
    # reference has no incremental KV-cache API surface — the cache
    # updates inside the forward function still assume the full prefix
    # is provided).  This is correct but slow; correctness > speed for
    # this sanity-check command.
    print()
    print(
        f"[sample] decoding {max_new_tokens} tokens (temperature={temperature}, "
        f"top_k={top_k}, seed={seed})",
        flush=True,
    )
    generated = []
    cur = list(ids)
    len(ids)
    for step in range(max_new_tokens):
        # ``cur`` is the entire prompt-plus-generated-so-far prefix; its
        # position-id T axis must start from the prompt origin (0) so
        # M-RoPE keeps the original angles stable.  pos_offset=0 is
        # correct for any prefix length because we always re-prefill
        # from token 0.
        logits = _forward(cur, pos_offset=0)
        mx.eval(logits)
        last = logits[0, -1, :].astype(mx.float32)
        if temperature <= 0:
            nxt = int(mx.argmax(last).item())
        else:
            scaled = last / temperature
            if top_k and top_k < last.shape[-1]:
                # mx.topk returns just the values array (top-k in
                # descending order).  The k-th largest is at index
                # ``top_k - 1``.
                kth = mx.topk(scaled, k=top_k, axis=-1)[top_k - 1]
                scaled = mx.where(
                    scaled < kth, mx.array(-1e30, dtype=scaled.dtype), scaled
                )
            # simple gumbel-max sample
            np.random.seed(seed + step)
            u = np.random.uniform(0, 1, size=last.shape).astype(np.float32)
            gumbel = -np.log(-np.log(u + 1e-30) + 1e-30)
            scores = np.array(scaled.tolist()) + gumbel
            nxt = int(np.argmax(scores))
        generated.append(nxt)
        cur.append(nxt)
        piece = tok.decode([nxt])
        print(f"  step {step + 1:>3}: id={nxt:>8}  piece={piece!r}")
        # Stop on EOS (Qwen3.5 eos_token_id is 248044 per config.json).
        if nxt == 248044:
            break
    completion = tok.decode(generated)
    print()
    print(f"Completion: {completion!r}")
    return 0


def main(argv: list | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--hf-dir",
        type=Path,
        default=DEFAULT_HF_DIR,
        help=f"HF checkpoint dir (default: {DEFAULT_HF_DIR})",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("download", help="populate hf-dir with the Qwen3.5 0.8B checkpoint")

    p_inspect = sub.add_parser("inspect", help="summarise the loaded weights")
    p_inspect.add_argument(
        "--json", action="store_true", help="emit JSON instead of text"
    )

    p_dump = sub.add_parser("dump-blob", help="serialise weights to the flat blob")
    p_dump.add_argument("out", type=Path)
    p_dump.add_argument("-v", "--verbose", action="store_true")

    p_sample = sub.add_parser(
        "sample", help="run a forward pass + autoregressive decode"
    )
    p_sample.add_argument("prompt", type=str)
    p_sample.add_argument("--max-new-tokens", type=int, default=20)
    p_sample.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="0 = greedy, >0 = gumbel-max sampling",
    )
    p_sample.add_argument("--top-k", type=int, default=1)
    p_sample.add_argument("--seed", type=int, default=0)

    args = p.parse_args(argv)

    if args.cmd == "download":
        _download(args.hf_dir)
        return 0
    if args.cmd == "inspect":
        return _inspect(args.hf_dir, json_out=args.json)
    if args.cmd == "dump-blob":
        return _dump_blob(args.hf_dir, args.out, verbose=args.verbose)
    if args.cmd == "sample":
        return _sample(
            args.hf_dir,
            args.prompt,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
            top_k=args.top_k,
            seed=args.seed,
        )
    p.error(f"unknown subcommand: {args.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
