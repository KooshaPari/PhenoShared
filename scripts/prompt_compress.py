#!/usr/bin/env python3
"""N20 — Prompt compression middleware (Forward DAG v2 §4.4/§6).
Trims context blocks via 'claim-stripped citation-only' mode for sub-agents.
Mandatory for any sub-agent prompt >100k tokens or >50kB.

Modes:
  --mode citation_only : keep only local://sha256 citations + claim stubs
  --mode claim_stripped: strip claim bodies, keep citations + headings

Usage:
  python scripts/prompt_compress.py --input prompt.md --mode citation_only --max-kb 50 --output prompt.compact.md
  python scripts/prompt_compress.py --text "long prompt..." --mode claim_stripped
"""

import argparse
import re
import sys
from pathlib import Path

CITATION_RE = re.compile(r"local://sha256/[0-9a-f]{64}")
CLAIM_RE = re.compile(r"\[([LP])\]")


def compress(text: str, mode: str) -> str:
    if mode == "citation_only":
        # Keep headings + citations, drop claim bodies
        lines = []
        for line in text.splitlines():
            if (
                line.startswith("#")
                or CITATION_RE.search(line)
                or CLAIM_RE.search(line)
                or line.strip() == ""
            ):
                lines.append(line)
        # Deduplicate citations
        seen = set()
        out = []
        for line in lines:
            cits = CITATION_RE.findall(line)
            if cits:
                for c in cits:
                    if c not in seen:
                        seen.add(c)
                        out.append(f"- {c}")
            else:
                out.append(line)
        return "\n".join(out)
    elif mode == "claim_stripped":
        # Keep headings + citations, strip [L]/[P] claim bodies to first sentence
        out_lines = []
        for line in text.splitlines():
            if CLAIM_RE.search(line):
                # Keep citation part, truncate claim to 120 chars
                m = CITATION_RE.search(line)
                cite = f" {m.group(0)}" if m else ""
                claim = line.split("]")[-1][:120].strip()
                out_lines.append(
                    f"- [{CLAIM_RE.search(line).group(1)}] {claim}...{cite}"
                )
            elif line.startswith("#") or CITATION_RE.search(line) or line.strip() == "":
                out_lines.append(line)
        return "\n".join(out_lines)
    else:
        return text


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, help="input file")
    p.add_argument("--text", type=str, help="inline text")
    p.add_argument("--output", type=Path, help="output file (default stdout)")
    p.add_argument(
        "--mode", choices=["citation_only", "claim_stripped"], default="citation_only"
    )
    p.add_argument(
        "--max-kb", type=int, default=50, help="threshold KB to trigger compression"
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="exit 2 if input > max-kb and not compressed, else 0",
    )
    args = p.parse_args()

    if args.input:
        text = args.input.read_text(encoding="utf-8", errors="ignore")
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()

    size_kb = len(text.encode("utf-8")) / 1024
    if args.check:
        if size_kb > args.max_kb:
            print(
                f"OVER {size_kb:.1f}KB > {args.max_kb}KB — compression required",
                file=sys.stderr,
            )
            sys.exit(2)
        print(f"OK {size_kb:.1f}KB <= {args.max_kb}KB", file=sys.stderr)
        sys.exit(0)

    if size_kb <= args.max_kb:
        out = text
        print(f"pass-through {size_kb:.1f}KB <= {args.max_kb}KB", file=sys.stderr)
    else:
        out = compress(text, args.mode)
        new_kb = len(out.encode("utf-8")) / 1024
        print(
            f"compressed {size_kb:.1f}KB -> {new_kb:.1f}KB ({args.mode})",
            file=sys.stderr,
        )

    if args.output:
        args.output.write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out)


if __name__ == "__main__":
    main()
