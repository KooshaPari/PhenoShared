#!/usr/bin/env bash
# scripts/migrate_50_beads.sh — run cockpit_migrator with --batch=50.
#
# v0.13 WBS-PERT-100 Phase 5 task 74 — migrate 50 beads.jsonl entries
# to AgilePlus in 50-bead chunks.
#
# Idempotent: re-running is safe (server-side hash dedup).
# Stop conditions:
#   - All beads migrated (returned cleanly)
#   - Any batch fails 3x in a row (aborts)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIGRATOR="${REPO_ROOT}/scripts/cockpit_migrator.py"
SOURCE="${PHENOTYPE_BEADS_JSONL:-${HOME}/CodeProjects/Phenotype/repos/phenotype-dag/beads.jsonl}"
BATCH="${PHENOTYPE_MIGRATE_BATCH:-50}"
BACKEND="${PHENOTYPE_MIGRATE_BACKEND:-agileplus}"
MAX_RETRIES="${PHENOTYPE_MIGRATE_MAX_RETRIES:-3}"

if [[ ! -f "$MIGRATOR" ]]; then
  echo "no migrator at $MIGRATOR" >&2
  exit 4
fi

echo "[migrate-50] repo=$REPO_ROOT source=$SOURCE batch=$BATCH backend=$BACKEND retries=$MAX_RETRIES"

# Idempotency: if verify reports zero missing, exit 0 immediately.
echo "[migrate-50] running verify first..."
if .venv/bin/python "$MIGRATOR" --verify --backend="$BACKEND" --source="$SOURCE" 2>&1 | tail -5; then
  rc="${PIPESTATUS[0]}"
  if [[ "$rc" == "0" ]]; then
    echo "[migrate-50] already migrated; exiting 0"
    exit 0
  fi
fi

attempt=0
while [[ $attempt -lt $MAX_RETRIES ]]; do
  attempt=$((attempt + 1))
  echo "[migrate-50] attempt $attempt/$MAX_RETRIES..."
  if ! .venv/bin/python "$MIGRATOR" \
      --execute \
      --backend="$BACKEND" \
      --batch="$BATCH" \
      --source="$SOURCE"; then
    echo "[migrate-50] attempt $attempt failed; retrying..." >&2
    sleep "$((attempt * 2))"
    continue
  fi
  echo "[migrate-50] attempt $attempt succeeded"
  exit 0
done

echo "[migrate-50] exhausted $MAX_RETRIES retries; aborting" >&2
exit 2
