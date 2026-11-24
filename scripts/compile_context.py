#!/usr/bin/env python3
"""CLI: compile context via Needle router/ranker/budget."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from needle.compiler import ContextCompiler


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--query", required=True)
    p.add_argument(
        "--candidates", type=Path, required=True, help="JSON list of {path, content?}"
    )
    p.add_argument("--role", default="")
    p.add_argument("--model", default="", help="Model name hint for router")
    args = p.parse_args()
    cands = json.loads(args.candidates.read_text(encoding="utf-8"))
    contents = {c["path"]: c.get("content", "") for c in cands}
    compiler = ContextCompiler()
    compiled = compiler.compile(
        args.query, cands, contents, model=args.model, header_role=args.role
    )
    print(compiler.render(compiled, contents))
    print("---")
    print(
        json.dumps(
            {
                "role": compiled.role,
                "token_estimate": compiled.token_estimate,
                "original_estimate": compiled.original_estimate,
                "reduction_ratio": round(compiled.reduction_ratio, 3),
                "slices": [{"path": s.path, "score": s.score} for s in compiled.slices],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
