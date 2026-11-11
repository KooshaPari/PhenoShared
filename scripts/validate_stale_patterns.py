#!/usr/bin/env python3
"""Fail on banned MCP anti-patterns in catalog and docs (ADR-017/018).

Two kinds of document legitimately name a retired pattern:

* append-only historical records, which state what happened as fact and must not
  be rewritten to satisfy a linter (`RECORD_PREFIXES` / `RECORD_FILES`);
* guidance that must name the ban in order to define it — the handbook entry for
  the anti-pattern, the ADRs that retired it.

The first group is declared once, by scope, because rewriting a record is worse
than exempting it. The second group declares itself in the file header:

    <!-- stale-patterns: file-allow=handbook entry that defines this ban -->

Every exemption is printed at build time, so the set of exempted lines stays
visible in CI logs rather than becoming invisible permission.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (pattern, human label) — scan catalog + docs only (not full git history).
# `mirror-to-empty` and `cheap-llm-mcp` are repo/pattern names, so they are
# anchored on word boundaries: `cheap-llm-mcp-deprecate` is a branch name and
# `mirror-to-empty-repo.md` is a filename, neither of which is a violation.
BANNED = [
    (
        r"(?<!never )(?<![\w-])mirror-to-empty(?![\w-])",
        "mirror-to-empty fork bootstrap",
    ),
    (r"(?<![\w-])cheap-llm-mcp(?![\w-])", "standalone cheap-llm MCP repo"),
    (
        r"PhenoFastMCP-rust\s+# tier-0 MCP framework fork \(rmcp\)",
        "rmcp mislabeled as PhenoFastMCP-rust parent",
    ),
    (
        r"phenotype-rust-sdk.*successor_role:\s*mcp-framework",
        "retired rust bucket as framework home",
    ),
]

SCAN_GLOBS = [
    "catalog/*.yaml",
    "docs/**/*.md",
    "README.md",
    "skills/**/*.md",
]

# Append-only records. These name retired repos as fact; the alternative to
# exempting them is falsifying or reformatting history. Scoped by directory (or
# by exact path where a single dated audit lives outside a record tree).
RECORD_PREFIXES = (
    "docs/monorepo-state/",
    "docs/org-audits/",
)
RECORD_FILES = ("docs/operations/sd-retire-audit-2026-06-17.md",)

FILE_MARKER = "stale-patterns: file-allow="
MIN_REASON = 12
FILE_MARKER_WINDOW = 10
COMMENT_TERMINATORS = ("-->", "--!>")


def record_scope(rel: str) -> str | None:
    """Return why `rel` is exempt as a historical record, if it is."""
    for prefix in RECORD_PREFIXES:
        if rel.startswith(prefix):
            return f"historical record tree ({prefix})"
    if rel in RECORD_FILES:
        return "historical record (dated audit)"
    return None


def _reason_after(line: str, marker: str) -> str | None:
    idx = line.lower().find(marker)
    if idx == -1:
        return None
    tail = line[idx + len(marker) :]
    # Justification runs to an HTML comment terminator or end of line.
    for stop in COMMENT_TERMINATORS:
        pos = tail.find(stop)
        if pos != -1:
            tail = tail[:pos]
            break
    return tail.strip()


def file_marker_reason(text: str) -> tuple[int | None, str | None]:
    """Return (lineno, reason) for a file-scoped marker in the header window."""
    for lineno, line in enumerate(text.splitlines()[:FILE_MARKER_WINDOW], start=1):
        reason = _reason_after(line, FILE_MARKER)
        if reason is not None:
            return lineno, reason
    return None, None


def scan_text(rel: str, text: str) -> tuple[list[str], list[str]]:
    """Return (failures, granted exemptions) for one file's contents."""
    scope = record_scope(rel)
    marker_lineno, marker_reason = file_marker_reason(text)
    failures: list[str] = []
    granted: list[str] = []

    file_scope = False
    if marker_lineno is not None:
        if len(marker_reason or "") < MIN_REASON:
            failures.append(
                f"{rel}:{marker_lineno}: file exemption marker needs a justification "
                f"of at least {MIN_REASON} characters, got {len(marker_reason or '')}"
            )
        else:
            file_scope = True

    for lineno, line in enumerate(text.splitlines(), start=1):
        if lineno == marker_lineno:
            # The header marker line itself carries no pattern to exempt.
            continue
        matched = [
            label for regex, label in BANNED if re.search(regex, line, re.IGNORECASE)
        ]
        if not matched:
            continue
        if scope is not None:
            for label in matched:
                granted.append(f"{rel}:{lineno}: {label} — {scope}")
            continue
        if file_scope:
            for label in matched:
                granted.append(f"{rel}:{lineno}: {label} — {marker_reason}")
            continue
        for label in matched:
            failures.append(f"{rel}:{lineno}: banned pattern ({label})")

    if file_scope and scope is None and not granted:
        failures.append(
            f"{rel}:{marker_lineno}: orphan file exemption marker (no banned pattern "
            f"in this file) — remove it"
        )
    return failures, granted


def iter_files():
    for pattern in SCAN_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            if not path.is_file():
                continue
            yield path.relative_to(ROOT).as_posix(), path


def main() -> int:
    failures: list[str] = []
    granted: list[str] = []
    scanned = 0
    for rel, path in iter_files():
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        file_failures, file_granted = scan_text(rel, text)
        failures.extend(file_failures)
        granted.extend(file_granted)

    for exemption in granted:
        print(f"EXEMPT: {exemption}")

    if failures:
        for failure in failures:
            print(f"STALE: {failure}")
        return 1

    print(
        f"OK no banned MCP patterns outside declared records "
        f"({scanned} files scanned, {len(granted)} justified exemptions)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
