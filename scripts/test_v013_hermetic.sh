#!/usr/bin/env bash
# scripts/test_v013_hermetic.sh — fast hermetic test subset for CI.
#
# v0.13 WBS-PERT-100 Phase 6 task 86 — CI quick check.
#
# Runs the v0.13 hermetic subset with fail-fast.
# Wall target: ≤ 30 seconds on a fast runner.
#
# Exit code:
#   0  all tests pass
#   1  any test fails
#   2  python not in PATH

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -d .venv ]]; then
  echo ".venv/ not found at $REPO_ROOT" >&2
  exit 2
fi

PY="${REPO_ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "python not found at $PY" >&2
  exit 2
fi

TESTS=(
  "tests/test_runtime_config.py"
  "tests/test_runtime_config_edge_cases.py"
  "tests/test_tracera_dual_write_sample.py"
  "tests/test_tracera_metrics.py"
  "tests/test_tracera_bridge_thread_safety.py"
  "tests/test_agileplus_adapter.py"
  "tests/test_agileplus_adapter_bulk.py"
  "tests/test_cockpit_migrator.py"
  "tests/test_forge_status.py"
  "tests/test_conftest_isolation.py"
  "tests/trace_store/test_runtime.py"
  "tests/test_tracera_ingest_dual_write.py"
)

echo "[v0.13-hermetic] running ${#TESTS[@]} test files"
echo "===================================================="

start=$(date +%s)
"${PY}" -m pytest -q -x "${TESTS[@]}"
rc=$?
end=$(date +%s)

elapsed=$((end - start))
echo "===================================================="
echo "[v0.13-hermetic] completed in ${elapsed}s (rc=${rc})"
exit "$rc"
