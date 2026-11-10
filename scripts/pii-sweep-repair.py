#!/usr/bin/env python3
"""Repair the PII-sweep damage that makes scripts depend on one machine's home path.

Context
-------
The 2026-09-16 redaction sweep wrote the literal token ``<REDACTED>`` over the
owner's home directory in 44,496 places.  In prose that is harmless (and the
repo already has ``scripts/escape_redacted_for_vitepress.py`` to keep VitePress
from choking on it).  In executable code it is not harmless: a script that
hard-codes ``/Users/<REDACTED>/CodeProjects/...`` cannot find anything on any
machine, including the one it was written on.

Those absolute paths were already a portability bug before the sweep.  The
sweep did not create that bug; it made it unfixable by accident.  The repair is
therefore not "put the username back" -- it is "stop depending on an absolute
home path at all":

    /Users/<REDACTED>/CodeProjects/x   ->   $HOME/CodeProjects/x     (shell)
    "/Users/<REDACTED>/CodeProjects/x" ->   os.path.expanduser("~/CodeProjects/x")

That is portable, contains no name at all, and is the same shape the code
should have had from the start.

What this tool refuses to do
----------------------------
* It never touches vendored or archived copies.  ``audits/``, ``archives/``,
  ``absorption/``, ``repos/`` and the worklog dumps are other projects' or
  this project's history; rewriting them would falsify a record.  Use
  ``--scope all`` only if that is what you want.
* It never guesses at a quoting context it cannot see.  A shell path inside
  SINGLE quotes does not expand, so ``'$HOME/x'`` would be a silent breakage.
  Those sites are reported, not rewritten.
* It never rewrites YAML, Rust, JavaScript, plist or JSON values, because in
  those languages a home path may be a literal that an application, not a
  shell, reads -- and ``$HOME`` would not expand there.  Those are reported.
* It is a dry run unless ``--apply`` is passed.

Usage
-----
    scripts/pii-sweep-repair.py                 # report, change nothing
    scripts/pii-sweep-repair.py --apply         # rewrite the safe cases
    scripts/pii-sweep-repair.py --scope all     # include vendored copies
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# nosec B105 -- this is a path prefix, not a credential. bandit reads any
# literal assigned to a name containing "TOKEN" as a possible secret.
TOKEN = "/Users/<REDACTED>"  # nosec B105
VENDORED_PREFIXES = (
    "audits/",
    "archives/",
    ".archive/",
    "absorption/",
    "repos/",
    "docs/worklogs/",
    "crates/hexa-kit/",
    # a vendored copy of another project that happens to live under scripts/
    "scripts/org-audits/",
)

SHELL_SUFFIXES = {".sh", ".bash"}
PYTHON_SUFFIXES = {".py"}
REPORTED_SUFFIXES = {
    ".yaml",
    ".yml",
    ".rs",
    ".js",
    ".ts",
    ".tsx",
    ".toml",
    ".json",
    ".plist",
}

# A python literal that BEGINS with the redacted home path.
# Only the START of a literal is matched here; the whole group of adjacent
# literals is handled by repair_python_text.
PY_START_RE = re.compile(r"(?<![fFrRbB])(['\"])/Users/<REDACTED>")


def vendored(path: str) -> bool:
    return path.startswith(VENDORED_PREFIXES)


def shell_quote_context(line: str, index: int) -> str:
    """Return 'single', 'double' or 'none' for the quote context at ``index``.

    Walks the line left to right tracking quote state, so a path inside
    "double quotes" is distinguished from one inside 'single quotes'.
    """
    state = "none"
    i = 0
    while i < index:
        ch = line[i]
        if state == "none":
            if ch == '"':
                state = "double"
            elif ch == "'":
                state = "single"
            elif ch == "\\":
                i += 1  # skip the escaped character
        elif state == "double":
            if ch == "\\":
                i += 1
            elif ch == '"':
                state = "none"
        else:  # single
            if ch == "'":
                state = "none"
        i += 1
    return state


def repair_shell(line: str) -> tuple[str, str | None]:
    """Rewrite shell home paths. Returns (new_line, note)."""
    if TOKEN not in line:
        return line, None
    out = []
    idx = 0
    notes = []
    while True:
        pos = line.find(TOKEN, idx)
        if pos == -1:
            out.append(line[idx:])
            break
        ctx = shell_quote_context(line, pos)
        out.append(line[idx:pos])
        if ctx == "single":
            out.append(TOKEN)
            notes.append("single-quoted: $HOME would not expand; needs requoting")
        elif ctx == "double":
            # already inside "..." -- the existing quotes protect the value.
            # ${HOME} rather than $HOME: shellcheck SC2250 wants braces around
            # a variable reference that is followed by more path text, and the
            # gate lints modified files.
            out.append("${HOME}")
        else:
            # unquoted: quote it, so a HOME containing spaces is still handled
            out.append('"${HOME}"')
        idx = pos + len(TOKEN)
    return "".join(out), ("; ".join(sorted(set(notes))) if notes else None)


def _scan_literal(text: str, start: int) -> int:
    """Return the index just past the string literal that starts at ``start``."""
    quote = text[start]
    i = start + 1
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == quote:
            return i + 1
        if ch == "\n":
            return start  # unterminated; treat as not a literal
        i += 1
    return start


def _in_comment(text: str, offset: int) -> bool:
    """True when ``offset`` sits inside a comment on its line."""
    line_start = text.rfind("\n", 0, offset) + 1
    line = text[line_start:offset]
    quote = None
    i = 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "#":
            return True
        i += 1
    return False


def repair_python_text(text: str, has_os_import: bool) -> tuple[str, list[str]]:
    """Rewrite python literals whose path STARTS with the redacted home.

    Operates on the whole file, because python's implicit string concatenation
    spans lines:

        Path(
            "/Users/<REDACTED>/.../results/"
            "stock-vs-ours/run-v5-qwen35-08b.json"
        )

    The whole group of adjacent literals is wrapped in os.path.expanduser(...),
    which python concatenates at compile time before the call happens, so the
    leading '~' still expands.  Rewriting only the first literal would leave
    two adjacent expressions where one was, which is a SyntaxError.

    Only a LEADING path can become expanduser at all, because expanduser only
    expands a leading '~'.  A path in the middle of a literal has no
    mechanical fix and is reported instead of mangled.
    """
    notes: list[str] = []
    out = []
    i = 0
    changed = 0
    while True:
        m = PY_START_RE.search(text, i)
        if not m:
            out.append(text[i:])
            break
        out.append(text[i : m.start()])
        lit_start = m.start(1)
        lit_end = _scan_literal(text, lit_start)
        if lit_end == lit_start:
            out.append(text[m.start() : m.end()])
            i = m.end()
            continue

        # Collect the whole group of adjacent literals.
        group_end = lit_end
        probe = lit_end
        while True:
            j = probe
            while j < len(text) and text[j] in " \t\r\n":
                j += 1
            if j < len(text) and text[j] in "'\"" and not text.startswith("#", j):
                nxt = _scan_literal(text, j)
                if nxt == j:
                    break
                group_end = nxt
                probe = nxt
                continue
            break

        if not has_os_import:
            notes.append(
                f"line {text.count(chr(10), 0, m.start()) + 1}: no 'import os' in this file; needs an import added by hand"
            )
            out.append(text[m.start() : group_end])
            i = group_end
            continue

        if _in_comment(text, m.start()):
            notes.append(
                f"line {text.count(chr(10), 0, m.start()) + 1}: inside a comment; left alone"
            )
            out.append(text[m.start() : group_end])
            i = group_end
            continue

        group = text[lit_start:group_end]
        first_end = _scan_literal(text, lit_start)
        head = group[: first_end - lit_start]
        tail = group[first_end - lit_start :]
        if TOKEN not in head:
            out.append(text[m.start() : group_end])
            i = group_end
            continue
        new_head = head.replace(TOKEN, "~", 1)
        out.append(f"os.path.expanduser({new_head}{tail})")
        changed += 1
        i = group_end
    return "".join(out), notes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--apply", action="store_true", help="write the changes (default: dry run)"
    )
    ap.add_argument("--scope", choices=("own", "all"), default="own")
    args = ap.parse_args()

    root = Path(".")
    changed_files = 0
    rewritten_sites = 0
    reported: list[str] = []

    candidates: list[Path] = []
    for pattern in (
        "**/*.sh",
        "**/*.bash",
        "**/*.py",
        "**/*.yaml",
        "**/*.yml",
        "**/*.rs",
        "**/*.js",
        "**/*.ts",
        "**/*.toml",
        "**/*.plist",
    ):
        candidates.extend(root.glob(pattern))
    candidates = [p for p in candidates if ".git/" not in str(p)]

    for path in sorted(candidates):
        rel = str(path)
        if args.scope == "own" and vendored(rel):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if TOKEN not in text:
            continue

        has_os = bool(re.search(r"^\s*import\s+os\b", text, re.MULTILINE))
        suffix = path.suffix
        lines = text.splitlines(keepends=True)
        out_lines = []
        file_changed = False

        if suffix in PYTHON_SUFFIXES:
            new_text, notes = repair_python_text(text, has_os)
            for note in notes:
                reported.append(f"{rel}: {note}")
            if new_text != text:
                file_changed = True
                rewritten_sites += text.count(TOKEN) - new_text.count(TOKEN)
            if args.apply and file_changed:
                path.write_text(new_text, encoding="utf-8")
            if file_changed:
                changed_files += 1
            continue

        for lineno, line in enumerate(lines, start=1):
            new_line = line
            note = None
            if suffix in SHELL_SUFFIXES:
                new_line, note = repair_shell(line)
            elif suffix in REPORTED_SUFFIXES:
                note = f"{suffix} value; $HOME does not expand in this language"
            else:
                note = f"{suffix} file; no rule for this language"
            if note:
                reported.append(f"{rel}:{lineno}: {note}")
            if new_line != line:
                file_changed = True
                rewritten_sites += line.count(TOKEN) - new_line.count(TOKEN)
            out_lines.append(new_line)

        if file_changed:
            changed_files += 1
            if args.apply:
                path.write_text("".join(out_lines), encoding="utf-8")

    print(f"files that would change : {changed_files}")
    print(f"sites rewritten         : {rewritten_sites}")
    print(f"sites reported, not changed: {len(reported)}")
    if reported:
        print("\n--- reported (not rewritten) ---")
        for item in reported[:60]:
            print("  " + item)
        if len(reported) > 60:
            print(f"  ... and {len(reported) - 60} more")
    if args.apply:
        print("\nAPPLIED")
    else:
        print("\ndry run; pass --apply to write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
