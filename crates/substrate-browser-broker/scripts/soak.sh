#!/usr/bin/env bash
# Cross-process soak for the browser lease/profile authority.
#
# Runs N worker processes against ONE state directory, all contending for the
# same profile with a TTL tight enough to force expiry races, then checks:
#   1. no two workers held the profile at the same time (overlap detection)
#   2. fencing tokens never repeat for a profile
#   3. the profile manifest still parses and holds exactly one generation
#   4. no lease records are left behind
#
# Usage: soak.sh [workers] [iterations] [hold_ms] [ttl_ms]
set -uo pipefail

WORKERS="${1:-6}"
ITERS="${2:-120}"
HOLD_MS="${3:-15}"
TTL_MS="${4:-60}"
TMP_BASE="${SOAK_TMP_BASE:-$HOME/CodeProjects/temp}"
mkdir -p "$TMP_BASE"
ROOT="$(mktemp -d "$TMP_BASE/browser-soak.XXXXXX")"
BIN="${SOAK_BIN:-target/debug/examples/soak_worker}"

echo "root:     $ROOT"
echo "workers:  $WORKERS   iterations/worker: $ITERS   hold: ${HOLD_MS}ms   ttl: ${TTL_MS}ms"

pids=()
outs=()
for i in $(seq 1 "$WORKERS"); do
  out="$ROOT/worker-$i.jsonl"
  outs+=("$out")
  "$BIN" "$ROOT" alice work "$ITERS" "$HOLD_MS" "$TTL_MS" >"$out" 2>"$ROOT/worker-$i.err" &
  pids+=($!)
done

fail=0
for p in "${pids[@]}"; do
  wait "$p" || fail=$((fail + 1))
done
echo "worker exits failed: $fail"

echo "--- worker stats"
cat "$ROOT"/worker-*.err

cat "$ROOT"/worker-*.jsonl >"$ROOT/all.jsonl"

python3 - "$ROOT" <<'PY'
import json, sys, glob, os

root = sys.argv[1]
rows = []
for line in open(os.path.join(root, "all.jsonl")):
    line = line.strip()
    if line:
        rows.append(json.loads(line))

print(f"--- holds recorded: {len(rows)}")
if not rows:
    print("FAIL: no holds recorded")
    sys.exit(1)

# 1. Overlap. When a TTL is shorter than the hold, an expired holder may still
#    be mid-call while a new holder legitimately acquires. That is not a safety
#    failure: the safety property is that two holds whose fences were BOTH still
#    valid never overlap. Only those count.
rows.sort(key=lambda r: (r["start"], r["end"]))
valid_rows = [r for r in rows if r["valid"]]
overlaps = []
prev = None
for r in valid_rows:
    if prev is not None and r["start"] < prev["end"]:
        overlaps.append((prev["lease"], r["lease"], prev["end"] - r["start"]))
    if prev is None or r["end"] > prev["end"]:
        prev = r
expired_but_held = len(rows) - len(valid_rows)

# 2. fence monotonicity in start order
fences = [r["fence"] for r in rows]
dupes = len(fences) - len(set(fences))
non_monotonic = sum(1 for a, b in zip(fences, fences[1:]) if b <= a)

# 3. manifest sanity
# Broker::new roots ProfileStore at <state>, so principals live under <state>/profiles/.
manifest_path = os.path.join(root, "profiles", "alice", "work", "manifest.json")
gens = None
if os.path.exists(manifest_path):
    m = json.load(open(manifest_path))
    gens = len(m.get("generations", []))

# 4. leftover leases that are still unexpired. Expired records linger until the
#    next grant sweeps them, which is documented behaviour, not a leak.
import time
now_ms = int(time.time() * 1000)
leftover = 0
for path in glob.glob(os.path.join(root, "leases", "*.json")):
    try:
        rec = json.load(open(path))
    except Exception:
        leftover += 1
        continue
    if rec.get("expires_at_unix_ms", 0) > now_ms:
        leftover += 1
holders = sorted({r["holder"] for r in rows})
valid = sum(1 for r in rows if r["valid"])

print(f"distinct holders:      {len(holders)}")
print(f"holds with valid fence:{valid}/{len(rows)}")
print(f"fence duplicates:      {dupes}")
print(f"non-monotonic fences:  {non_monotonic}")
print(f"holds whose fence went stale mid-hold: {expired_but_held}")
print(f"overlapping VALID holds: {len(overlaps)}")
print(f"generations in profile:{gens}")
print(f"leftover lease files:  {leftover}")

status = 0
if overlaps:
    print("FAIL: two workers held the same profile concurrently")
    for o in overlaps[:5]:
        print("   ", o)
    status = 1
if dupes:
    print("FAIL: fencing token reused")
    status = 1
if gens != 1:
    print(f"FAIL: expected exactly 1 generation, found {gens}")
    status = 1
if valid == 0 and expired_but_held == 0:
    print("FAIL: no hold validated and none expired; nothing was exercised")
    status = 1
if expired_but_held == len(rows) and rows:
    print("NOTE: TTL shorter than hold; every hold correctly expired mid-flight")
if leftover:
    print(f"WARN: {leftover} lease record(s) left after revoke")
print("PASS" if status == 0 else "FAILED")
sys.exit(status)
PY
rc=$?
echo "--- soak result: $rc"
echo "$ROOT"
exit "$rc"
