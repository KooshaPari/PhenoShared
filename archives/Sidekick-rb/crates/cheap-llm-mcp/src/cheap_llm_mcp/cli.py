from __future__ import annotations

import argparse
import asyncio
import json
import sys

from .config import load as load_config
from .ledger import Ledger
from .router import Router


async def _run(args: argparse.Namespace) -> None:
    r = Router(load_config())
    try:
        if args.stream:
            async for chunk in r.stream(
                args.prompt,
                provider=args.provider,
                variant=args.variant,
                model=args.model,
                system=args.system,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
            ):
                sys.stdout.write(chunk)
                sys.stdout.flush()
            sys.stdout.write("\n")
            return
        result = await r.complete(
            args.prompt,
            provider=args.provider,
            variant=args.variant,
            model=args.model,
            system=args.system,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )
        if args.json:
            print(
                json.dumps(
                    {
                        "text": result.text,
                        "model": result.model,
                        "provider": result.provider,
                        "input_tokens": result.input_tokens,
                        "output_tokens": result.output_tokens,
                    },
                    indent=2,
                )
            )
        else:
            print(result.text)
    finally:
        await r.aclose()


async def _doctor() -> int:
    cfg = load_config()
    r = Router(cfg)
    rc = 0
    print("cheap-llm doctor — probing providers...")
    for name in cfg.providers:
        try:
            p = r._get(name)
            out = await p.health()
            ok = out["status"] == "ok"
            rc |= 0 if ok else 1
            mark = "✓" if ok else "✗"
            print(f"  {mark} {name:10s} {out['latency_ms']}ms  {out.get('error', '')}")
        except Exception as e:
            rc |= 1
            print(f"  ✗ {name:10s} setup error: {type(e).__name__}: {e}")
    # Ledger summary
    ledger = Ledger(
        path=__import__("pathlib").Path.home() / ".cheap-llm" / "ledger.jsonl",
        cap_usd=cfg.monthly_cost_cap_usd,
    )
    agg = ledger.month_total()
    print(f"\nThis month: ${agg.total_usd:.4f} across {agg.calls} calls")
    if cfg.monthly_cost_cap_usd is not None:
        print(
            f"Cap:        ${cfg.monthly_cost_cap_usd:.2f}  "
            f"(remaining ${cfg.monthly_cost_cap_usd - agg.total_usd:.4f})"
        )
    await r.aclose()
    return rc


def main() -> None:
    p = argparse.ArgumentParser(prog="cheap-llm", description="Cheap-LLM CLI")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("doctor", help="Health-check all providers + show cost summary")

    # Default command: completion
    p.add_argument("prompt", nargs="?", help="Prompt text. If omitted, read from stdin.")
    p.add_argument("--provider", default="auto", choices=["auto", "minimax", "kimi", "fireworks"])
    p.add_argument("--variant", default="highspeed")
    p.add_argument("--model", default=None)
    p.add_argument("--system", default=None)
    p.add_argument("--max-tokens", type=int, default=4096)
    p.add_argument("--temperature", type=float, default=0.2)
    p.add_argument("--stream", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    if args.cmd == "doctor":
        sys.exit(asyncio.run(_doctor()))
    if args.prompt is None:
        args.prompt = sys.stdin.read()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
