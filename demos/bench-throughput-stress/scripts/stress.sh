#!/usr/bin/env bash
# pheno-harness bench throughput stress driver.
set -euo pipefail
N="${N:-8}"
DURATION_S="${duration_s:-15}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
[ -f "${REPO_ROOT}/bench/cli.py" ] || { echo "bench/cli.py not found"; exit 1; }

# Probe once: get available suites
SUITES=$(cd "$REPO_ROOT" && PYTHONPATH=. python3 bench/cli.py list 2>/dev/null | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin)
    print(" ".join(s["name"] for s in d.get("suites",[])))
except: print("small medium")')
if [ -z "$SUITES" ]; then SUITES="small medium"; fi
echo "[bench-throughput-stress] suites: $SUITES"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_JSONL="${HERE}/../artifacts/runs.jsonl"
mkdir -p "$(dirname "$OUT_JSONL")"
: > "$OUT_JSONL"

STOP_FILE="$(mktemp -u)"
( sleep "$DURATION_S"; touch "$STOP_FILE" ) &

for ((i=0;i<N;i++)); do
  (
    while [ ! -f "$STOP_FILE" ]; do
      pick=$((RANDOM % 4))
      suite=$(echo $SUITES | cut -d' ' -f$((pick + 1)))
      [ -z "$suite" ] && suite="small"
      t_start=$(date +%s%N)
      out=$(cd "$REPO_ROOT" && PYTHONPATH=. python3 bench/cli.py info "$suite" 2>&1) || true
      rc=$?
      t_end=$(date +%s%N)
      lat_ms=$(( (t_end - t_start) / 1000000 ))
      passed=$(echo "$out" | grep -oE '"passed":[ ]*(true|false)' | head -1 || echo "")
      printf '{"worker":%d,"suite":"%s","lat_ms":%d,"exit_code":%d,"check":"info"}\n' \
        "$i" "$suite" "$lat_ms" "$rc" >> "$OUT_JSONL"
    done
  ) &
done
wait
rm -f "$STOP_FILE"

echo "wrote $OUT_JSONL ($(wc -l < "$OUT_JSONL") runs)"
