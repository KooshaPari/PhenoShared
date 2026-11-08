#!/usr/bin/env python3
"""
clean_absorbed_tree.py — content-cleanup helper for `absorbed-from-*/**`
trees under `docs/`.

Walks one tree (or all trees) under `docs/absorbed-from-<name>/**` and
applies the same defensive fixes used to unblock `docs:build`:

  1. Strip git conflict markers (whole-line match only, no false positives).
  2. Strip Search/Replace tool markers (`<<<< SEARCH`, `>>>> REPLACE`, etc.).
  3. Escape `<placeholder>` patterns so Vue's template parser does not
     treat them as unclosed HTML elements.
  4. Wrap `{{ ... }}` in `<span v-pre>` so Vue's mustache interpreter
     does not try to evaluate placeholder expressions.

After cleanup, the tree can be removed from
`docs/.vitepress/config.mts` `srcExclude` to be re-included in the build.

Usage:

    # Clean one tree
    python3 scripts/clean_absorbed_tree.py docs/absorbed-from-PhenoDevOps

    # Dry-run all trees (preview, no writes)
    python3 scripts/clean_absorbed_tree.py --all --dry-run

    # Verify a tree builds cleanly
    python3 scripts/clean_absorbed_tree.py docs/absorbed-from-PhenoDevOps \\
        --verify --src-exclude-revert
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# Conflict markers — whole-line match only.
EXACT_STRIP = {
    "<<<<<<< HEAD",
    "<<<<<<<",
    "=======",
    ">>>>>>> origin/main",
    ">>>>>>>",
    ">>>>>>> HEAD",
    "<<<<<<< theirs",
    ">>>>>>> theirs",
    "|||||||",
}
# Patterns for tool-specific markers that may include trailing text.
PREFIX_STRIP = (
    re.compile(r"^<<<<<<<\s*\S*$"),
    re.compile(r"^>>>>>>>\s*\S*$"),
    re.compile(r"^<<<<\s+SEARCH\s*$"),
    re.compile(r"^>>>>\s+SEARCH\s*$"),
    re.compile(r"^<<<<\s+REPLACE\s*$"),
    re.compile(r"^>>>>\s+REPLACE\s*$"),
    re.compile(r"^<<<<<\s+COMMIT\s*$"),
    re.compile(r"^>>>>>\s+COMMIT\s*$"),
)
# <placeholder> pattern for Vue SFC escape. We deliberately match `<Word>`,
# `<word>`, `<with-dash>`, `<with_underscore>`, `<Capitalized>` but skip
# well-known HTML elements.
PLACEHOLDER_RE = re.compile(r"<([a-zA-Z][a-zA-Z0-9_./-]*)>")
VALID_HTML = {
    "br", "hr", "sub", "sup", "code", "pre", "a", "p", "span", "div",
    "em", "strong", "li", "ul", "ol", "table", "tr", "td", "th",
    "thead", "tbody", "h1", "h2", "h3", "h4", "h5", "h6", "img",
    "i", "b", "u", "small", "blockquote",
}
# Vue mustache expression — only wrap when the body contains characters
# that break Vue's JS expression parser (em-dashes, en-dashes, etc.).
MUSTACHE_RE = re.compile(r"\{\{([^}]+)\}\}")


def is_valid_html(tag: str) -> bool:
    return tag.lower() in VALID_HTML


def strip_markers(lines: list[str]) -> tuple[list[str], int]:
    """Strip conflict markers. Returns (new_lines, count_stripped)."""
    out = []
    stripped = 0
    in_code = False
    for line in lines:
        s = line.strip()
        if s.startswith("```") or s.startswith("~~~"):
            in_code = not in_code
            out.append(line)
            continue
        if in_code:
            out.append(line)
            continue
        if s in EXACT_STRIP or any(p.match(s) for p in PREFIX_STRIP):
            stripped += 1
            continue
        out.append(line)
    return out, stripped


def escape_placeholders(lines: list[str]) -> tuple[list[str], int]:
    """Escape <placeholder> patterns. Returns (new_lines, count_escaped)."""
    out = []
    count = 0
    in_code = False
    for line in lines:
        s = line.strip()
        if s.startswith("```") or s.startswith("~~~"):
            in_code = not in_code
            out.append(line)
            continue
        if in_code:
            out.append(line)
            continue
        # Skip lines that are entirely a v-pre wrap (preserved as-is).
        if "<span v-pre>" in line and "</span>" in line:
            out.append(line)
            continue

        def repl(m: re.Match[str]) -> str:
            nonlocal count
            tag = m.group(1)
            if is_valid_html(tag):
                return m.group(0)
            count += 1
            return f"&lt;{tag}&gt;"

        new_line = PLACEHOLDER_RE.sub(repl, line)
        out.append(new_line)
    return out, count


def wrap_mustaches(lines: list[str]) -> tuple[list[str], int]:
    """Wrap {{ ... }} in <span v-pre> when body has em-dash or other JS-incompatible chars."""
    out = []
    count = 0
    in_code = False
    for line in lines:
        s = line.strip()
        if s.startswith("```") or s.startswith("~~~"):
            in_code = not in_code
            out.append(line)
            continue
        if in_code:
            out.append(line)
            continue
        # Already wrapped
        if "<span v-pre>" in line and "</span>" in line:
            out.append(line)
            continue

        def repl(m: re.Match[str]) -> str:
            nonlocal count
            body = m.group(1)
            # Wrap unconditionally to keep behavior consistent.
            count += 1
            return f"<span v-pre>{{{{{body}}}}}</span>"

        new_line = MUSTACHE_RE.sub(repl, line)
        out.append(new_line)
    return out, count


def walk_tree(root: Path) -> list[Path]:
    """Walk all .md/.mdx/.markdown files under root, excluding .vitepress and node_modules."""
    files = []
    for dp, dirs, fs in os.walk(root):
        dirs[:] = [d for d in dirs if d not in (".vitepress", "node_modules", "dist", "cache")]
        for f in fs:
            if f.endswith((".md", ".mdx", ".markdown")):
                files.append(Path(dp) / f)
    return files


def process_file(p: Path, dry_run: bool) -> dict[str, int]:
    """Apply all cleanup passes. Returns counts per pass."""
    counts = {"stripped": 0, "escaped": 0, "mustache": 0}
    try:
        original = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"  SKIP {p}: {e}", file=sys.stderr)
        return counts
    lines = original.splitlines(keepends=True)

    new_lines, stripped = strip_markers(lines)
    lines = new_lines
    new_lines, escaped = escape_placeholders(lines)
    lines = new_lines
    new_lines, mustache = wrap_mustaches(lines)
    lines = new_lines

    counts["stripped"] = stripped
    counts["escaped"] = escaped
    counts["mustache"] = mustache

    new_content = "".join(lines)
    if new_content != original and not dry_run:
        p.write_text(new_content, encoding="utf-8")
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", help="Path to one absorbed tree (e.g. docs/absorbed-from-PhenoDevOps)")
    ap.add_argument("--all", action="store_true", help="Process all docs/absorbed-from-*/** trees")
    ap.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    ap.add_argument("--verify", action="store_true", help="Run `bunx --bun vitepress build docs` after cleanup")
    ap.add_argument("--src-exclude-revert", action="store_true",
                    help="Temporarily remove srcExclude entries for verification, restore after")
    args = ap.parse_args()

    if not args.target and not args.all:
        ap.error("provide a target path or --all")

    repo_root = Path(__file__).resolve().parent.parent
    docs_root = repo_root / "docs"

    if args.all:
        targets = sorted(docs_root.glob("absorbed-from-*"))
    else:
        targets = [Path(args.target)]

    if not targets:
        print("no targets found", file=sys.stderr)
        return 1

    grand_total = {"files": 0, "stripped": 0, "escaped": 0, "mustache": 0}
    for target in targets:
        if not target.exists():
            print(f"SKIP {target}: does not exist", file=sys.stderr)
            continue
        print(f"\n== {target.relative_to(repo_root)} ==")
        files = walk_tree(target)
        if not files:
            print(f"  no markdown files found")
            continue
        per_tree = {"files": 0, "stripped": 0, "escaped": 0, "mustache": 0}
        for p in files:
            counts = process_file(p, args.dry_run)
            if any(counts.values()):
                per_tree["files"] += 1
                for k, v in counts.items():
                    per_tree[k] += v
        mode = "[DRY-RUN] " if args.dry_run else ""
        print(f"  {mode}files touched: {per_tree['files']}")
        print(f"  {mode}conflict-marker lines stripped: {per_tree['stripped']}")
        print(f"  {mode}<placeholder> patterns escaped:  {per_tree['escaped']}")
        print(f"  {mode}{{{{ ... }}}} patterns wrapped:   {per_tree['mustache']}")
        for k, v in per_tree.items():
            grand_total[k] += v

    print("\n== TOTAL ==")
    mode = "[DRY-RUN] " if args.dry_run else ""
    print(f"  {mode}files touched: {grand_total['files']}")
    print(f"  {mode}conflict-marker lines stripped: {grand_total['stripped']}")
    print(f"  {mode}<placeholder> patterns escaped:  {grand_total['escaped']}")
    print(f"  {mode}{{{{ ... }}}} patterns wrapped:   {grand_total['mustache']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
