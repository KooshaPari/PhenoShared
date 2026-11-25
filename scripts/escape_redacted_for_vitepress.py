#!/usr/bin/env python3
"""Escape literal `<REDACTED>` redaction tokens that break the VitePress build.

Background
----------
A redaction sweep wrote the literal token ``<REDACTED>`` into documentation
prose. VitePress compiles every Markdown page into a Vue SFC, so a raw
``<REDACTED>`` in prose is parsed by the Vue template compiler as an
*unclosed HTML element* and the build aborts with:

    [vite:vue] [plugin vite:vue] <file>.md (4:40): Element is missing end tag.

What this script changes
------------------------
Only prose text nodes:

    <REDACTED>   ->   &lt;REDACTED&gt;

``&lt;REDACTED&gt;`` is an HTML entity, so the page still *renders* the
literal text ``<REDACTED>``; it just no longer looks like a tag.

What this script never changes
-------------------------------
Contexts that are already safe, or that are code rather than prose:

* fenced code blocks (``` / ~~~)  -- markdown-it already escapes their content
* inline code spans (`...`)        -- markdown-it already escapes their content
* Markdown link / image destinations -- markdown-it percent-encodes them, and
  escaping here would corrupt the URL (``&lt;`` -> ``%26lt%3B``)
* reference-style link definitions  -- same reason as inline destinations
* Vue interpolations ``{{ ... }}`` -- a JS/TS expression context
* ``<script>`` / ``<style>`` blocks  -- a JS/TS/CSS context
* HTML attribute values            -- a quoted attribute value may legally
  contain ``<``; the Vue compiler accepts it (verified with @vue/compiler-sfc)
* HTML comments                    -- stripped by the compiler
* already-escaped ``&lt;REDACTED&gt;`` -- never re-escaped (idempotent)

Usage
-----
    # dry run: report what would change
    python3 scripts/escape_redacted_for_vitepress.py --root . --check

    # apply
    python3 scripts/escape_redacted_for_vitepress.py --root . --apply

    # restrict the scope
    python3 scripts/escape_redacted_for_vitepress.py --root . \
        --markdown-root docs --vue-root .vitepress --apply
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

TOKEN = "<REDACTED>"
ESCAPED = "&lt;REDACTED&gt;"

FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
TAG_START_RE = re.compile(r"<[A-Za-z!/?]")
ATTR_VALUE_RE = re.compile(r"=\s*(\"[^\"]*\"|'[^']*')")
INTERP_RE = re.compile(r"\{\{.*?\}\}", re.DOTALL)
LINK_DEST_OPEN_RE = re.compile(r"\]\(")
REF_DEF_RE = re.compile(r"(?m)^ {0,3}\[[^\]\n]+\]:[ \t]*(<[^>\n]*>|\S+)")
SCRIPT_BLOCK_RE = re.compile(r"<script\b[^>]*>.*?</script\s*>", re.DOTALL | re.IGNORECASE)
STYLE_BLOCK_RE = re.compile(r"<style\b[^>]*>.*?</style\s*>", re.DOTALL | re.IGNORECASE)
VUE_BLOCK_RE = re.compile(
    r"<(template|script|style)\b([^>]*)>(.*?)</\1\s*>", re.DOTALL | re.IGNORECASE
)

SKIP_DIR_NAMES = {"node_modules", "dist", ".git", ".vitepress", ".cache"}


# --------------------------------------------------------------------------- #
# protection mask helpers
# --------------------------------------------------------------------------- #


def _protect(mask: bytearray, start: int, end: int) -> None:
    """Mark [start, end) of `mask` as protected (do not rewrite)."""
    if end > start:
        mask[start:end] = b"\x01" * (end - start)


def _protect_match(mask: bytearray, match: re.Match[str]) -> None:
    _protect(mask, match.start(), match.end())


def mark_fenced_code(text: str, mask: bytearray) -> None:
    """Protect fenced code blocks (``` / ~~~), including their fence lines."""
    offset = 0
    fence_char: str | None = None
    fence_len = 0
    for line in text.split("\n"):
        match = FENCE_RE.match(line)
        info = (match.group(2) or "").strip() if match else ""
        if fence_char is None:
            if match and not (match.group(1)[0] == "`" and "`" in info):
                fence_char = match.group(1)[0]
                fence_len = len(match.group(1))
                _protect(mask, offset, offset + len(line))
        else:
            _protect(mask, offset, offset + len(line))
            closes = (
                match is not None
                and match.group(1)[0] == fence_char
                and len(match.group(1)) >= fence_len
                and not (fence_char == "`" and info)
            )
            if closes:
                fence_char = None
        offset += len(line) + 1


def mark_inline_code(text: str, mask: bytearray) -> None:
    """Protect CommonMark inline code spans (backtick runs).

    Code spans are resolved *per line* rather than per file. A stray unmatched
    backtick in one table row would otherwise pair with a backtick many rows
    later and mask a whole region as "code", which silently skipped real prose
    occurrences. markdown-it parses inline content per block, so a per-line
    bound is also closer to what the renderer actually does.
    """
    offset = 0
    for line in text.split("\n"):
        n = len(line)
        i = 0
        while i < n:
            if line[i] != "`" or mask[offset + i]:
                i += 1
                continue
            j = i
            while j < n and line[j] == "`":
                j += 1
            run_len = j - i
            k = j
            close_end: int | None = None
            while k < n:
                if line[k] == "`" and not mask[offset + k]:
                    m = k
                    while m < n and line[m] == "`":
                        m += 1
                    if m - k == run_len:
                        close_end = m
                        break
                    k = m
                else:
                    k += 1
            if close_end is None:
                i = j
                continue
            _protect(mask, offset + i, offset + close_end)
            i = close_end
        offset += n + 1


def mark_html_comments(text: str, mask: bytearray) -> None:
    for match in HTML_COMMENT_RE.finditer(text):
        _protect_match(mask, match)


def mark_html_attribute_values(text: str, mask: bytearray) -> None:
    """Protect quoted attribute values inside raw HTML tags.

    The tag *name* is deliberately not protected: `<REDACTED>` used as a tag
    name is exactly the construct that breaks the Vue compiler.
    """
    n = len(text)
    i = 0
    while i < n:
        if text[i] != "<" or mask[i]:
            i += 1
            continue
        if not TAG_START_RE.match(text, i):
            i += 1
            continue
        j = i + 1
        quote: str | None = None
        while j < n:
            ch = text[j]
            if quote is not None:
                if ch == quote:
                    quote = None
            elif ch in "\"'":
                quote = ch
            elif ch == ">":
                break
            j += 1
        if j >= n:
            # No closing '>' -- not a tag (e.g. a bare "<" in prose). Do not
            # treat the remainder of the file as a tag: that would mask prose.
            i += 1
            continue
        tag = text[i : j + 1]
        for attr in ATTR_VALUE_RE.finditer(tag):
            _protect(mask, i + attr.start(), i + attr.end())
        i = j + 1


def mark_link_destinations(text: str, mask: bytearray) -> None:
    """Protect Markdown inline link/image destinations."""
    n = len(text)
    for match in LINK_DEST_OPEN_RE.finditer(text):
        start = match.end()
        if start >= n:
            continue
        if text[start] == "<":
            end = text.find(">", start)
            if end != -1:
                _protect(mask, start, end + 1)
            continue
        depth = 1
        k = start
        while k < n and depth:
            ch = text[k]
            if ch == "\\":
                k += 2
                continue
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        _protect(mask, start, min(k + 1, n))


def mark_reference_definitions(text: str, mask: bytearray) -> None:
    for match in REF_DEF_RE.finditer(text):
        # keep the "[label]:" prefix visible, protect only the destination
        dest_start = match.start(1)
        _protect(mask, dest_start, match.end())


def mark_interpolations(text: str, mask: bytearray) -> None:
    for match in INTERP_RE.finditer(text):
        _protect_match(mask, match)


def mark_script_style_blocks(text: str, mask: bytearray) -> None:
    for regex in (SCRIPT_BLOCK_RE, STYLE_BLOCK_RE):
        for match in regex.finditer(text):
            _protect_match(mask, match)


# --------------------------------------------------------------------------- #
# per-format handlers
# --------------------------------------------------------------------------- #


def markdown_mask(text: str) -> bytearray:
    """Build the protection mask for a Markdown page."""
    mask = bytearray(len(text))
    mark_fenced_code(text, mask)
    mark_inline_code(text, mask)
    mark_html_comments(text, mask)
    mark_script_style_blocks(text, mask)
    mark_link_destinations(text, mask)
    mark_reference_definitions(text, mask)
    mark_interpolations(text, mask)
    mark_html_attribute_values(text, mask)
    return mask


def vue_mask(text: str) -> bytearray:
    """Build the protection mask for a Vue SFC.

    `<script>` / `<style>` blocks are JS/TS/CSS context and are protected
    wholesale; inside `<template>` only comments, attribute values and
    interpolations are protected.
    """
    mask = bytearray(len(text))
    for match in VUE_BLOCK_RE.finditer(text):
        tag = match.group(1).lower()
        body_start = match.start(3)
        body_end = match.end(3)
        if tag in ("script", "style"):
            _protect(mask, match.start(), match.end())
            continue
        inner = text[body_start:body_end]
        inner_mask = bytearray(len(inner))
        mark_html_comments(inner, inner_mask)
        mark_html_attribute_values(inner, inner_mask)
        mark_interpolations(inner, inner_mask)
        for idx, flag in enumerate(inner_mask):
            if flag:
                mask[body_start + idx] = 1
    # Any <script>/<style> block not matched by the balanced regex above.
    mark_script_style_blocks(text, mask)
    return mask


def escape_unprotected(text: str, mask: bytearray) -> tuple[str, int]:
    """Replace TOKEN with ESCAPED everywhere the mask is not set."""
    out: list[str] = []
    cursor = 0
    changed = 0
    for match in re.finditer(re.escape(TOKEN), text):
        start, end = match.span()
        if any(mask[start:end]):
            continue
        out.append(text[cursor:start])
        out.append(ESCAPED)
        cursor = end
        changed += 1
    out.append(text[cursor:])
    return "".join(out), changed


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #


@dataclass
class Scope:
    """One VitePress scope: a Markdown source root and/or a Vue theme root."""

    label: str
    markdown_roots: list[Path] = field(default_factory=list)
    vue_roots: list[Path] = field(default_factory=list)


@dataclass
class FileResult:
    path: str
    kind: str
    occurrences: int


def _iter_files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    out: list[Path] = []
    if not root.exists():
        return out
    if root.is_file():
        return [root] if root.suffix in suffixes else []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        if any(part in SKIP_DIR_NAMES for part in path.relative_to(root).parts[:-1]):
            continue
        out.append(path)
    return out


def process_scope(scope: Scope, apply: bool) -> list[FileResult]:
    results: list[FileResult] = []
    for md_root in scope.markdown_roots:
        for path in _iter_files(md_root, (".md",)):
            original = path.read_text(encoding="utf-8")
            if TOKEN not in original:
                continue
            updated, count = escape_unprotected(original, markdown_mask(original))
            if count:
                results.append(FileResult(str(path), "markdown", count))
                if apply:
                    path.write_text(updated, encoding="utf-8")
    for vue_root in scope.vue_roots:
        for path in _iter_files(vue_root, (".vue",)):
            original = path.read_text(encoding="utf-8")
            if TOKEN not in original:
                continue
            updated, count = escape_unprotected(original, vue_mask(original))
            if count:
                results.append(FileResult(str(path), "vue-sfc", count))
                if apply:
                    path.write_text(updated, encoding="utf-8")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument(
        "--markdown-root",
        action="append",
        default=[],
        help="Markdown source root to process (repeatable)",
    )
    parser.add_argument(
        "--vue-root",
        action="append",
        default=[],
        help="Vue SFC root to process (repeatable)",
    )
    parser.add_argument(
        "--label", default="default", help="scope label used in the report"
    )
    parser.add_argument(
        "--check", action="store_true", help="report only, do not write files"
    )
    parser.add_argument("--apply", action="store_true", help="write the changes")
    parser.add_argument("--json", action="store_true", help="emit a JSON report")
    args = parser.parse_args(argv)

    if args.check == args.apply:
        parser.error("choose exactly one of --check or --apply")

    root = Path(args.root).resolve()
    scope = Scope(
        label=args.label,
        markdown_roots=[(root / p).resolve() for p in args.markdown_root],
        vue_roots=[(root / p).resolve() for p in args.vue_root],
    )
    if not scope.markdown_roots and not scope.vue_roots:
        parser.error("at least one --markdown-root or --vue-root is required")

    results = process_scope(scope, apply=args.apply)

    files = len(results)
    occurrences = sum(r.occurrences for r in results)
    by_kind: dict[str, int] = {}
    for r in results:
        by_kind[r.kind] = by_kind.get(r.kind, 0) + r.occurrences

    if args.json:
        print(
            json.dumps(
                {
                    "scope": scope.label,
                    "mode": "apply" if args.apply else "check",
                    "files_changed": files,
                    "occurrences_changed": occurrences,
                    "occurrences_by_kind": by_kind,
                    "files": [
                        {"path": r.path, "kind": r.kind, "occurrences": r.occurrences}
                        for r in results
                    ],
                },
                indent=2,
            )
        )
        return 0

    print(f"scope            : {scope.label}")
    print(f"mode             : {'apply' if args.apply else 'check'}")
    print(f"files changed    : {files}")
    print(f"occurrences      : {occurrences}")
    for kind, count in sorted(by_kind.items()):
        print(f"  {kind:<13}: {count}")
    for r in results:
        print(f"  {r.occurrences:>4}  {r.kind:<10} {r.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
