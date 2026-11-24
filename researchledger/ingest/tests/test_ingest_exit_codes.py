"""Every ingest/finalize script must propagate its failure to the process exit code.

The corpus scripts each carry a guard of the shape::

    if <nothing landed>:
        print("  ERROR: ...")
        return 1

That guard is only real if the ``__main__`` block feeds ``main()``'s return value
into ``sys.exit``. A bare ``main()`` discards it, the interpreter exits 0, and a
total ingestion loss is indistinguishable from success to any caller: CI, cron,
a wrapper lane, or a human reading ``echo $?``.

Observed 2026-11-10: ``claude_desktop_build_canonical.py`` ended with a bare
``main()`` while all four of its siblings used ``sys.exit(main())``. Its own
"0 canonical items landed" guard could therefore never fail a pipeline. Fixed
here, and pinned so a new script cannot silently repeat it.

This is a static check on purpose: importing these modules executes argparse at
import time, and running them needs the production corpus. The invariant is
structural, so structure is what gets asserted.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ANALYSIS_DIR = Path(__file__).resolve().parent.parent

# Scripts that mutate a corpus and therefore must report failure by exit code.
# Matched by name shape rather than an explicit list so a newly added migrator
# is covered the moment it lands.
INGEST_SCRIPT_GLOBS = ("*migrate*.py", "*build_canonical*.py", "*_to_research.py")


def _ingest_scripts() -> list[Path]:
    found: set[Path] = set()
    for pattern in INGEST_SCRIPT_GLOBS:
        found.update(ANALYSIS_DIR.glob(pattern))
    return sorted(p for p in found if p.is_file())


def _main_guard(module: ast.Module) -> ast.If | None:
    """Return the top-level ``if __name__ == "__main__":`` block, if any."""
    for node in module.body:
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "__name__"
        ):
            continue
        comparators = [ast.dump(c) for c in test.comparators]
        if any("'__main__'" in c for c in comparators):
            return node
    return None


def _exits_with_main(block: ast.If) -> bool:
    """True when the block wraps main() in sys.exit(...) / SystemExit."""
    for node in ast.walk(ast.Module(body=block.body, type_ignores=[])):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # sys.exit(main())
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "exit"
            and isinstance(func.value, ast.Name)
            and func.value.id == "sys"
        ):
            if any(isinstance(a, ast.Call) for a in node.args):
                return True
        # raise SystemExit(main())
        if isinstance(func, ast.Name) and func.id == "SystemExit":
            if any(isinstance(a, ast.Call) for a in node.args):
                return True
    return False


def test_ingest_scripts_are_discovered() -> None:
    """Guard the guard: the glob must actually match the corpus scripts."""
    scripts = _ingest_scripts()
    names = {p.name for p in scripts}
    assert "claude_desktop_build_canonical.py" in names
    assert "claude_desktop_migrate_to_research.py" in names
    assert len(scripts) >= 5, f"expected the corpus scripts, found {sorted(names)}"


@pytest.mark.parametrize("script", _ingest_scripts(), ids=lambda p: p.name)
def test_ingest_script_propagates_exit_code(script: Path) -> None:
    """main()'s return value must reach the process exit status."""
    module = ast.parse(script.read_text(), filename=str(script))
    block = _main_guard(module)
    assert block is not None, (
        f"{script.name} has no `if __name__ == \"__main__\":` block, so its "
        "ERROR guards cannot affect the exit code"
    )
    assert _exits_with_main(block), (
        f"{script.name} calls main() without sys.exit(...), so a guard that "
        "prints ERROR and returns 1 still exits 0. Use `sys.exit(main())`."
    )
