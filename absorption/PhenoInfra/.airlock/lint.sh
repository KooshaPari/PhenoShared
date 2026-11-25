#!/usr/bin/env bash
set -euo pipefail

BASE_SHA="${AIRLOCK_BASE_SHA:-$(git rev-parse HEAD~1)}"
HEAD_SHA="${AIRLOCK_HEAD_SHA:-$(git rev-parse HEAD)}"

FILES="$(git diff --name-only "$BASE_SHA" "$HEAD_SHA" -- '*.md' '*.yml' '*.yaml' '*.json' '*.toml' '*.ts' '*.tsx' '*.js' '*.mjs' '*.cjs' '*.py' 2>/dev/null || true)"

if [ -z "$FILES" ]; then
  echo "No changed files detected for lint."
  exit 0
fi

echo "Airlock doc-focused lint no-op: verifying git state only."
git diff --name-only "$BASE_SHA" "$HEAD_SHA" >/dev/null
exit 0
