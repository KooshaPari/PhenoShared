#!/usr/bin/env bash
# bench_harness_smoke.sh — smoke-test the bench harness skeleton.
#
# Verifies:
#   1. `python -m bench --help` runs cleanly.
#   2. `python -m bench --self-test` exits 0 and round-trips JSON.
#   3. `pytest tests/test_bench_skeleton.py -v` passes 8+ tests.
#   4. `python -c "import bench; print(bench.__version__)"` runs.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PY="${PYTHON:-python}"
PYTEST_BIN="${PYTEST_BIN:-pytest}"

echo "[smoke] bench --help"
"$PY" -m bench --help

echo "[smoke] bench --self-test (no --self-test-output)"
"$PY" -m bench --self-test

echo "[smoke] bench --self-test (with --self-test-output)"
TMP_OUT="$(mktemp -t bench-self-test.XXXXXX.json)"
"$PY" -m bench self-test --self-test-output "$TMP_OUT"
test -s "$TMP_OUT" || { echo "[smoke] FAIL: empty self-test output"; exit 1; }
"$PY" -c "import json,sys; from bench.types import SuiteResult; \
  json.loads(open(sys.argv[1]).read()); sys.exit(0)" "$TMP_OUT"
rm -f "$TMP_OUT"

echo "[smoke] pytest tests/test_bench_skeleton.py"
PYTHONPATH="$REPO_ROOT" "$PYTEST_BIN" tests/test_bench_skeleton.py -v

echo "[smoke] bench module importable"
"$PY" -c "import bench; print(bench.__version__)" || exit 1

echo "[smoke] OK"
