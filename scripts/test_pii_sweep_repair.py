#!/usr/bin/env python3
"""Tests for scripts/pii-sweep-repair.py.

The first version of the repair rule replaced only the PREFIX of a python
literal:

    "/Users/<REDACTED>/x"   ->   os.path.expanduser("~/x"

which leaves the literal's own closing quote paired with the wrong
parenthesis.  ``Path("...")`` became ``Path(os.path.expanduser("~/x")`` -- one
paren short, a SyntaxError, in 22 files.  These tests exist so that class of
mistake cannot come back unnoticed.

Run:  python3 scripts/test_pii_sweep_repair.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "pii_sweep_repair", Path(__file__).with_name("pii-sweep-repair.py")
)
if spec is None or spec.loader is None:
    raise SystemExit("could not load scripts/pii-sweep-repair.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

FAILURES: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        FAILURES.append(f"{name}\n     got: {got!r}\n    want: {want!r}")


def check_shell(name: str, line: str, want: str) -> None:
    got, _note = mod.repair_shell(line)
    check(name, got, want)


def check_python(name: str, text: str, want: str, has_os: bool = True) -> None:
    got, _notes = mod.repair_python_text(text, has_os)
    check(name, got, want)


# --- shell -----------------------------------------------------------------
check_shell(
    "shell: double quoted",
    'cd "/Users/<REDACTED>/CodeProjects/x"',
    'cd "${HOME}/CodeProjects/x"',
)
check_shell(
    "shell: unquoted",
    "cd /Users/<REDACTED>/CodeProjects/x",
    'cd "${HOME}"/CodeProjects/x',
)
check_shell(
    "shell: single quoted is refused",
    "cd '/Users/<REDACTED>/x'",
    "cd '/Users/<REDACTED>/x'",
)
check_shell(
    "shell: single quoted reports a note",
    mod.repair_shell("cd '/Users/<REDACTED>/x'")[1],
    "single-quoted: $HOME would not expand; needs requoting",
)
check_shell(
    "shell: two occurrences on one line",
    "cp /Users/<REDACTED>/a /Users/<REDACTED>/b",
    'cp "${HOME}"/a "${HOME}"/b',
)
check_shell(
    "shell: a line with no token is untouched",
    "echo hello",
    "echo hello",
)

# --- python ----------------------------------------------------------------
check_python(
    "python: whole literal",
    'OUT = Path("/Users/<REDACTED>/CodeProjects/x")',
    'OUT = Path(os.path.expanduser("~/CodeProjects/x"))',
)
check_python(
    "python: bare literal",
    'P = "/Users/<REDACTED>/x"',
    'P = os.path.expanduser("~/x")',
)
check_python(
    "python: single quoted literal",
    "P = '/Users/<REDACTED>/x'",
    "P = os.path.expanduser('~/x')",
)
check_python(
    "python: mid-literal is refused",
    'P = "prefix /Users/<REDACTED>/x"',
    'P = "prefix /Users/<REDACTED>/x"',
)
check_python(
    "python: f-string is refused",
    'P = f"/Users/<REDACTED>/{name}"',
    'P = f"/Users/<REDACTED>/{name}"',
)
check_python(
    "python: comment line is refused",
    '# see "/Users/<REDACTED>/x"',
    '# see "/Users/<REDACTED>/x"',
)
check_python(
    "python: missing import os is refused",
    'P = Path("/Users/<REDACTED>/x")',
    'P = Path("/Users/<REDACTED>/x")',
    has_os=False,
)

# --- the property that actually broke -------------------------------------
# Every python rewrite must still parse.  This is the check that would have
# caught the original bug immediately.
SAMPLES = [
    'OUT = Path("/Users/<REDACTED>/CodeProjects/Phenotype/repos/cockpit")',
    'A = "/Users/<REDACTED>/x"; B = "/Users/<REDACTED>/y"',
    'ROOT = Path("/Users/<REDACTED>/CodeProjects/Phenotype/pheno-harness")',
    'D = {"k": "/Users/<REDACTED>/v"}',
    # implicit concatenation, on one line
    'P = Path("/Users/<REDACTED>/results/" "run-v5.json")',
    # implicit concatenation, across lines -- the case that broke the
    # line-at-a-time version
    'P = Path(\n    "/Users/<REDACTED>/results/"\n    "run-v5.json"\n)',
]
for sample in SAMPLES:
    out, _notes = mod.repair_python_text(sample, True)
    try:
        compile(out, "<sample>", "exec")
    except SyntaxError as exc:
        FAILURES.append(
            f"python rewrite does not compile: {sample!r} -> {out!r} ({exc})"
        )

# The concatenated group must survive as ONE argument, not two expressions.
concat_in = 'P = Path(\n    "/Users/<REDACTED>/results/"\n    "run-v5.json"\n)'
concat_out, _n = mod.repair_python_text(concat_in, True)
if "expanduser" not in concat_out or '"run-v5.json"' not in concat_out:
    FAILURES.append(f"concatenated group not wrapped: {concat_out!r}")

if FAILURES:
    print(f"FAILED: {len(FAILURES)} check(s)")
    for failure in FAILURES:
        print("  - " + failure)
    sys.exit(1)

print("all checks passed")
