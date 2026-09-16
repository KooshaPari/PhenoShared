#!/usr/bin/env bash
# scripts/run_hermetic_tests.sh — run the hermetic test subset.
#
# "Hermetic" means: no network, no MLX, no harbor, no docker.
# Useful as a CI smoke gate that does not require the optional
# external toolchain. The full suite lives at pytest.ini; the
# hermetic subset is curated by the -m hermetic marker.
#
# Usage:
#   bash scripts/run_hermetic_tests.sh            # default subset
#   bash scripts/run_hermetic_tests.sh --full     # full pytest with no extra skips
#   bash scripts/run_hermetic_tests.sh --collect  # list tests that would run

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

FULL=0
COLLECT_ONLY=0
PYTEST_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --full)     FULL=1 ;;
    --collect)  COLLECT_ONLY=1 ;;
    -h|--help)
      sed -n '2,16p' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    *)          PYTEST_ARGS+=("$arg") ;;
  esac
done

SUBSET_FILE="$REPO_ROOT/tests/hermetic_subset.txt"

if [ "$FULL" -eq 1 ]; then
  echo "[hermetic] full mode (no extra skips beyond marker-based ones)"
  if [ "$COLLECT_ONLY" -eq 1 ]; then
    exec python -m pytest --collect-only -q "${PYTEST_ARGS[@]}"
  fi
  exec python -m pytest "${PYTEST_ARGS[@]}"

elif [ "$COLLECT_ONLY" -eq 1 ]; then
  echo "[hermetic] subset collect-only"
  if [ -f "$SUBSET_FILE" ]; then
    mapfile -t subset_paths < <(grep -v -E '^\s*(#|$)' "$SUBSET_FILE")
    exec python -m pytest --collect-only -q "${subset_paths[@]}" "${PYTEST_ARGS[@]}"
  else
    exec python -m pytest -m "hermetic" --collect-only -q "${PYTEST_ARGS[@]}"
  fi

else
  echo "[hermetic] running subset (skip mlx/harbor/docker/network-bound)"
  if [ -f "$SUBSET_FILE" ]; then
    mapfile -t subset_paths < <(grep -v -E '^\s*(#|$)' "$SUBSET_FILE")
    FALLBACK_TESTS_DEFAULT_INSECURE=0 \
      exec python -m pytest "${subset_paths[@]}" "${PYTEST_ARGS[@]}"
  else
    FALLBACK_TESTS_DEFAULT_INSECURE=0 \
      exec python -m pytest -m "hermetic" "${PYTEST_ARGS[@]}"
  fi
fi
