#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "$0")/.." && pwd)
guard="$repo_root/bin/pheno"

set +e
output=$("$guard" 2>&1)
status=$?
set -e

test "$status" -eq 127
grep -Fq 'unavailable: no authorized pheno deployment is installed' <<<"$output"
grep -Fq 'does not run the unproven /usr/local/bin/pheno fallback' <<<"$output"
