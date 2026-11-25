#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "$0")/.." && pwd)
guard="$repo_root/bin/agileplus-worklog"

set +e
output=$("$guard" 2>&1)
status=$?
set -e

test "$status" -eq 127
grep -Fq 'unavailable: no authorized AgilePlus worklog deployment is installed' <<<"$output"
grep -Fq 'does not invoke the missing historical converter or unreleased source command' <<<"$output"
