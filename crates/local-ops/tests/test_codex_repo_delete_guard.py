#!/usr/bin/env python3
"""Regression corpus for the Codex repository-deletion PreToolUse guard."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
GUARD = Path(os.environ.get("CODEX_REPO_DELETE_GUARD", REPO_ROOT / "guards" / "codex-repo-delete-guard.sh"))
FAIL_CLOSED = "BLOCKED: unable to inspect pre-tool input safely."


def payload(command: object) -> bytes:
    return json.dumps({"tool": "Bash", "command": command}).encode()


def input_payload(command: object) -> bytes:
    return json.dumps({"tool": "Bash", "input": command}).encode()


def expect(label: str, expected: int, raw: bytes, *, missing_python: bool = False) -> None:
    environment = os.environ.copy()
    if missing_python:
        environment["PATH"] = "/nonexistent"
    try:
        completed = subprocess.run(
            ["/bin/bash", str(GUARD)],
            input=raw,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
            env=environment,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssertionError(f"{label}: exceeded 2 seconds") from exc

    output = (completed.stdout + completed.stderr).decode("utf-8", errors="replace")
    if completed.returncode != expected:
        raise AssertionError(
            f"{label}: expected exit {expected}, got {completed.returncode}; output={output!r}"
        )
    if "SENTINEL" in output or '"command"' in output:
        raise AssertionError(f"{label}: guard leaked payload: {output!r}")
    if expected == 1 and label in {"malformed_json", "non_string", "oversized", "missing_python"}:
        if output.strip() != FAIL_CLOSED:
            raise AssertionError(f"{label}: expected fixed diagnostic, got {output!r}")


def main() -> int:
    expect("newline_split", 1, payload("gh\nrepo\ndelete owner/SENTINEL"))
    expect("quoted_split", 1, payload("gh 'repo' \"delete\" owner/SENTINEL"))
    expect("shell_separator", 1, payload("printf benign; gh repo delete owner/SENTINEL"))
    expect("nested_shell", 1, payload("sh -c 'gh repo delete owner/SENTINEL'"))
    expect("env_wrapper", 1, payload("env GH_TOKEN=redacted gh repo delete owner/SENTINEL"))
    expect("sudo_wrapper", 1, payload("sudo -u operator gh repo delete owner/SENTINEL"))
    expect("command_wrapper", 1, payload("command -- gh repo delete owner/SENTINEL"))
    expect("curl_late_delete", 1, payload("curl https://api.github.com/repos/owner/SENTINEL -X DELETE"))
    expect("curl_short_attached", 1, payload("curl https://api.github.com/repos/owner/SENTINEL -XDELETE"))
    expect("curl_long_equals", 1, payload("curl --request=DELETE https://api.github.com/repos/owner/SENTINEL"))
    expect("thegent_existing_category", 1, payload("thegent repo delete owner/SENTINEL"))
    expect("forge_existing_category", 1, payload("forge repo delete owner/SENTINEL"))
    expect("input_field", 1, input_payload("gh repo delete owner/SENTINEL"))
    expect("quoted_data_argument", 0, payload("printf 'gh repo delete owner/SENTINEL'"))
    expect("unquoted_data_arguments", 0, payload("printf '%s' gh repo delete owner/SENTINEL"))
    expect("benign", 0, payload("printf harmless"))
    expect("malformed_json", 1, b"{not-json")
    expect("non_string", 1, payload(["gh", "repo", "delete"]))
    expect("oversized", 1, payload("x" * 65536))
    expect("missing_python", 1, payload("printf harmless"), missing_python=True)
    print("PASS codex-repo-delete-guard corpus")
    return 0


if __name__ == "__main__":
    sys.exit(main())
