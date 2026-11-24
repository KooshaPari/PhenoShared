"""Extract the final model reply from forge -p output.

Forge prints a spinner with reasoning lines interleaved, then the final
answer, then ``● Finished ...``.  We want only the last non-empty line
before ``● Finished``.
"""

from __future__ import annotations

import re

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")

_KEEP_PATTERNS = [
    re.compile(r"\x1b\[2m●\x1b\[0m (.*)"),
    re.compile(r"○\s*(.*)"),
]


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from *text*."""
    return _ANSI_RE.sub("", text)


def _extract_reply(raw: str) -> str:
    """Return the last non-empty line before ``● Finished`` in *raw*."""
    cleaned = _strip_ansi(raw)
    # Find the last occurrence of "● Finished" or "Finished"
    lines = cleaned.split("\n")
    # We want lines from after the last "●" that's not "Finished"
    last_segment_lines: list[str] = []
    for line in reversed(lines):
        stripped = line.strip()
        if "Finished" in stripped:
            continue
        if not stripped or stripped == "●":
            continue
        # Skip lines that are just spinner markers
        if stripped.startswith("●"):
            break  # reached the previous spinner
        last_segment_lines.insert(0, stripped)

    # Filter out the Initialize header line if present
    answer_lines = [line for line in last_segment_lines if "Initialize" not in line]
    # Return the last non-empty non-spinner line
    for line in reversed(answer_lines):
        if line.strip():
            return line.strip()
    # Fallback: return everything after stripping
    fallback = cleaned.strip()
    if "Finished" in fallback:
        fallback = fallback.rsplit("Finished", 1)[0].strip()
    return fallback


if __name__ == "__main__":
    # Quick smoke test
    sample = (
        "● [02:58:59] Initialize fb7cf433\n"
        "The user is asking a simple math question.\n"
        "\n"
        "2+2 =4\n"
        "\n"
        "4\n"
        "● [02:59:10] Finished fb7cf433\n"
    )
    print(repr(_extract_reply(sample)))
    assert _extract_reply(sample) == "4"  # nosec B101
    print("PASS")
