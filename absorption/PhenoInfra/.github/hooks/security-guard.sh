#!/usr/bin/env bash
set -euo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$HOOK_DIR/../.." && pwd)"

# In CI, run against all files since there are no staged changes
ALL_FILES_FLAG=""
if [ "${CI:-}" = "true" ] || [ "${GITHUB_ACTIONS:-}" = "true" ]; then
  ALL_FILES_FLAG="--all-files"
fi

if command -v uv >/dev/null 2>&1; then
  cd "$PROJECT_ROOT"
  uv sync --group dev
  # shellcheck disable=SC2086
  uv run pre-commit run --hook-stage pre-commit --config "$PROJECT_ROOT/.pre-commit-config.yaml" --show-diff-on-failure $ALL_FILES_FLAG
  exit $?
fi

if [ -x "$PROJECT_ROOT/.venv/bin/pre-commit" ]; then
  PRE_COMMIT="$PROJECT_ROOT/.venv/bin/pre-commit"
elif command -v pre-commit >/dev/null 2>&1; then
  PRE_COMMIT="pre-commit"
else
  echo "pre-commit executable not found; install uv (https://docs.astral.sh/uv/) or: pip install pre-commit"
  exit 1
fi

# shellcheck disable=SC2086
"$PRE_COMMIT" run --hook-stage pre-commit --config "$PROJECT_ROOT/.pre-commit-config.yaml" --show-diff-on-failure $ALL_FILES_FLAG
