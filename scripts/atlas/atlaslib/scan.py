"""Streaming file scanner.

Every tracked file is read exactly once, in fixed-size chunks, so no whole file
is ever held in memory (the repository has multi-megabyte tracked blobs). Each
pass accumulates the newline count used for LOC, the presence of the redaction
marker, test-declaration counts, entrypoint evidence, and `target_os` gating.
"""

from __future__ import annotations

import os
import stat

from .definitions import (
    CARRY,
    CHUNK,
    CODE_EXT,
    CODE_MAGICS,
    DOC_EXT,
    P_CFG_OS,
    P_MAIN_GO,
    P_MAIN_RS,
    P_TEST_GO,
    P_TEST_JS,
    P_TEST_PY,
    P_TEST_RS,
    REDACTED,
    TEXT_EXT,
)

ENTRY_BASENAMES = frozenset(
    "main.rs __main__.py main.py main.go index.js index.ts main.ts cli.ts "
    "server.ts index.mjs".split()
)


def _patterns_for(ext: str):
    """(regex, metric, line_anchored) triples for an extension."""
    if ext == "rs":
        return ((P_TEST_RS, "tests", False), (P_MAIN_RS, "main", False), (P_CFG_OS, "os", False))
    if ext == "py":
        return ((P_TEST_PY, "tests", True),)
    if ext == "go":
        return ((P_TEST_GO, "tests", True), (P_MAIN_GO, "main", True))
    if ext in ("ts", "tsx", "js", "jsx", "mjs", "mts", "cjs", "svelte", "vue", "astro"):
        return ((P_TEST_JS, "tests", True),)
    return ()


def scan_file(root: str, rel: str) -> dict:
    """Scan one tracked path. Never raises; unreadable files degrade to a record."""
    rec = {
        "path": rel, "kind": "reg", "size": 0, "loc": 0, "nl_end": True,
        "binary": False, "tests": 0, "main": False, "shebang": False, "exec": False,
        "redacted": 0, "os_cfg": (), "magic": b"", "readable": True,
    }
    abs_path = os.path.join(root, rel)
    try:
        st = os.lstat(abs_path)
    except OSError:
        rec["kind"], rec["readable"] = "missing", False
        return rec
    if stat.S_ISLNK(st.st_mode):
        rec["kind"], rec["readable"] = "link", False
        return rec
    if not stat.S_ISREG(st.st_mode):
        rec["kind"], rec["readable"] = "other", False
        return rec
    rec["exec"] = bool(st.st_mode & 0o111)

    ext = os.path.splitext(rel)[1].lstrip(".").lower()
    text_scan = ext in TEXT_EXT
    patterns = _patterns_for(ext)
    seen: dict[str, set] = {}
    os_hits: set[str] = set()

    carry, base, newlines, last = b"", 0, 0, b""
    try:
        with open(abs_path, "rb") as fh:
            first = True
            while True:
                chunk = fh.read(CHUNK)
                if not chunk:
                    break
                if first:
                    rec["magic"] = chunk[:4]
                    rec["shebang"] = chunk[:2] == b"#!"
                    first = False
                newlines += chunk.count(b"\n")
                last = chunk[-1:]
                rec["size"] += len(chunk)
                if text_scan:
                    data = carry + chunk
                    origin = base - len(carry)
                    for rx, metric, anchored in patterns:
                        marks = seen.setdefault(metric, set())
                        for match in rx.finditer(data):
                            offset = origin + match.start()
                            if offset in marks:
                                continue
                            # Line-anchored patterns are validated against the
                            # real preceding byte rather than re.M, so a match
                            # is never invented at a chunk boundary.
                            if anchored and offset and data[match.start() - 1:match.start()] != b"\n":
                                continue
                            marks.add(offset)
                            if metric == "os":
                                os_hits.add(match.group(1).decode("ascii", "replace"))
                            else:
                                rec[metric] += 1
                    if REDACTED in data:
                        rec["redacted"] += data.count(REDACTED)
                base += len(chunk)
                carry = (carry + chunk)[-CARRY:]
    except OSError:
        rec["kind"], rec["readable"] = "other", False
        return rec

    # LOC = newline count, plus one when a non-empty file does not end in a
    # newline. Deliberately stricter than `wc -l` so the 350/500 gate cannot
    # undercount a file by one line.
    rec["loc"] = newlines + (1 if rec["size"] and last != b"\n" else 0)
    rec["nl_end"] = not rec["size"] or last == b"\n"
    rec["os_cfg"] = tuple(sorted(os_hits))
    rec["binary"] = rec["magic"][:4] in CODE_MAGICS
    if os.path.basename(rel) in ENTRY_BASENAMES or "/src/bin/" in rel:
        rec["main"] = True
    if rec["shebang"] and rec["exec"] and not rec["main"]:
        rec["main"] = True
    if ext not in CODE_EXT and ext not in DOC_EXT:
        rec["main"] = False
    return rec


def scan_all(root: str, paths: list[str]) -> dict[str, dict]:
    return {rel: scan_file(root, rel) for rel in paths}
