#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "$0")/.." && pwd)

for command in atoms-auth kwatch; do
  guard="$repo_root/bin/$command"

  set +e
  output=$("$guard" 2>&1)
  status=$?
  set -e

  test "$status" -eq 127
  grep -Fq "$command unavailable: no authorized deployment is installed" <<<"$output"
  grep -Fq 'This guard does not run the preserved unproven binary fallback.' <<<"$output"
done
