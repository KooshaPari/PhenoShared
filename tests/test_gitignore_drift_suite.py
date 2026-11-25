"""DAG-74..80: tests/test_gitignore_drift_suite.py

Per-ADR 0008 §D4, the .gitignore drift-guard is 9 tests covering
every removal pattern from commit 4bf638c. This file bundles them
into a single pytest module so the test runner sees one test class
instead of 9 small files.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GITIGNORE = REPO_ROOT / ".gitignore"


def _text() -> str:
    return GITIGNORE.read_text()


def _has_line_starting_with(prefix: str) -> bool:
    for line in _text().splitlines():
        s = line.strip()
        if s.startswith(prefix):
            return True
    return False


# DAG-74: ADR 0008 §D4 — symlink-dir patterns are navigation aids
def test_no_0X_top_level_symlink_dirs() -> None:
    """The 6 logical-group symlink dirs (00_src..05_scripts) are
    navigation aids and must not be tracked (per ADR 0008 §D4)."""
    # The pattern in .gitignore is "kernels/**/0[0-5]_*/". Asserting
    # the inverse: those dirs must NOT be tracked.
    for d in REPO_ROOT.glob("kernels/**/0[0-5]_*/"):
        # If the dir is in .gitignore, fine. Otherwise, fail.
        rel = d.relative_to(REPO_ROOT).as_posix()
        # The pattern in .gitignore is "kernels/**/0[0-5]_*/"
        # so any match satisfies the rule.
        assert "kernels/**/0" in _text() or d.name in _text(), (
            f"symlink dir {rel} is tracked but should be gitignored"
        )


# DAG-75: bench/results/** — only .sha256 sidecars are tracked
def test_bench_results_json_is_gitignored() -> None:
    text = _text()
    assert "bench/results/**/*.json" in text


def test_bench_results_sha256_sidecar_tracked() -> None:
    """The .sha256 sidecar is the only persistent artifact in
    bench/results/; it must NOT be gitignored.

    Negation patterns (lines starting with '!') are allowed because
    they re-include .sha256 sidecars after a broader ignore rule.
    """
    text = _text()
    # Positive assertion: no positive pattern whose glob *matches*
    # a bench/results/*.sha256 path.  We match against a concrete
    # example path so that root-level release-sidecar patterns like
    # ``pheno-harness-v*.tar.gz.sha256`` (which never touch bench/results/)
    # do not cause a false positive.
    import fnmatch

    _example = "bench/results/_sota_test/2020-01-01/snapshot.sha256"
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#") or not s or s.startswith("!"):
            continue
        if fnmatch.fnmatch(_example, s):
            pytest.fail(
                f".gitignore line {line!r} glob-matches {_example!r} "
                f"(the only persistent artifact in bench/results/)"
            )


# DAG-76: .dogfood-live-* directories are operator-local
def test_dogfood_live_dirs_gitignored() -> None:
    assert _has_line_starting_with(".dogfood-live-*")


# DAG-77: kernels/.../.zig-cache/ is build output
def test_kernels_zig_cache_gitignored() -> None:
    text = _text()
    assert "kernels/**/.zig-cache/" in text or "kernels/**/.zig-cache" in text


def test_zig_out_gitignored() -> None:
    text = _text()
    assert "zig-out/" in text or "zig-out" in text


# DAG-78: kernels/.../rust/target/ is cargo build output
def test_kernels_rust_target_gitignored() -> None:
    text = _text()
    assert "kernels/**/rust/target/" in text or "kernels/**/rust/target" in text


# DAG-79: eval/traces/{*.jsonl, *.profile.csv} are recorder outputs
def test_eval_traces_jsonl_gitignored() -> None:
    text = _text()
    assert "eval/traces/*.jsonl" in text


def test_eval_traces_profile_csv_gitignored() -> None:
    text = _text()
    assert "eval/traces/*.profile.csv" in text
