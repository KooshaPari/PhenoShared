#!/usr/bin/env bash
# Phase 0 bootstrap (macOS / Linux) — mirror of install_phase0.ps1.
# Requires Python 3.10+ and OmniRoute storage.sqlite (default ~/.omniroute/storage.sqlite).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OMNIROUTE_DB="${OMNIROUTE_DB:-$HOME/.omniroute/storage.sqlite}"
SKIP_DEPS=0
SKIP_BENCH=0

usage() {
  cat <<'EOF'
Usage: bash scripts/install_phase0.sh [--skip-deps] [--skip-bench] [--db PATH]

  --skip-deps   Skip pip install -r requirements.txt
  --skip-bench  Skip bench_ik_llama.py --dry-run
  --db PATH     OmniRoute SQLite (default: ~/.omniroute/storage.sqlite)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-deps) SKIP_DEPS=1; shift ;;
    --skip-bench) SKIP_BENCH=1; shift ;;
    --db) OMNIROUTE_DB="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ ! -f "$OMNIROUTE_DB" ]]; then
  echo "OmniRoute DB not found: $OMNIROUTE_DB" >&2
  echo "Override with --db or set OMNIROUTE_DB. For deps-only smoke, use scripts/smoke_install.sh." >&2
  exit 1
fi

PY="${PYTHON:-python3}"

echo "==> pheno-harness Phase 0 (root: $ROOT)"

if [[ "$SKIP_DEPS" -eq 0 ]]; then
  echo "==> Installing Python dependencies"
  "$PY" -m pip install -r requirements.txt
  "$PY" -m pip install -e ".[dev]"
fi

echo "==> Exporting OmniRoute training data"
"$PY" scripts/export_omniroute_training.py --db "$OMNIROUTE_DB"

echo "==> Backfilling routing_decisions from call_logs"
"$PY" scripts/sync_routing_decisions.py --db "$OMNIROUTE_DB" --backfill

echo "==> Installing Pheno middleware hooks (sqlite)"
"$PY" scripts/install_middleware.py --db "$OMNIROUTE_DB" --mode sqlite

if [[ "$SKIP_BENCH" -eq 0 ]]; then
  echo "==> Running ik_llama baseline bench (dry-run)"
  "$PY" scripts/bench_ik_llama.py --dry-run
fi

echo "==> Phase 0 complete"
echo "  Training exports: $HOME/.omniroute/training"
echo "  Bench results:    $ROOT/bench/results"
echo "  Sync state:       $ROOT/state/routing_sync.json"
echo ""
echo "Restart OmniRoute to load middleware hooks from SQLite."
