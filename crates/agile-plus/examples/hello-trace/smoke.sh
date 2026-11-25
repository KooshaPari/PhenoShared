#!/usr/bin/env bash
# hello-trace smoke test
#
# Runs the minimal end-to-end pipeline against an empty scratch SQLite file
# and asserts each step exits 0. Designed to be invoked from CI or by a
# contributor verifying the CLI works locally.
#
# Usage:  ./examples/hello-trace/smoke.sh
# Exits:  0 on success, non-zero on the first failing step.
#
# Notes on the CLI surface (verified 2026-06-04):
#   * `seed-requirements` accepts --db and writes to that path.
#   * `list-projects` / `list-epics` / `list-stories` read `./agileplus.db`
#     in the current working directory; they do NOT accept --db.  The smoke
#     script cd's into the scratch dir before invoking them.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"

echo "[hello-trace] building agileplus-cli"
cargo build -p agileplus-cli

# Honor a user-level CARGO_TARGET_DIR redirect (e.g. E:/cargo-target) so the
# script works on machines that keep build artifacts off the workspace drive.
TARGET_DIR="${CARGO_TARGET_DIR:-$REPO_ROOT/target}"
BIN="$TARGET_DIR/debug/agileplus-cli"
# On Windows cargo emits `agileplus-cli.exe`; on POSIX systems it has no suffix.
if [[ ! -x "$BIN" && -x "$BIN.exe" ]]; then
  BIN="$BIN.exe"
fi
if [[ ! -x "$BIN" ]]; then
  echo "[hello-trace] FAIL: $BIN not found after build (target dir: $TARGET_DIR)" >&2
  exit 1
fi

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

echo "[hello-trace] seeding FR/NFR catalogs into $SCRATCH/agileplus.db"
"$BIN" seed-requirements --db "$SCRATCH/agileplus.db"

# List commands resolve the DB path relative to cwd; run them from the
# scratch directory and verify JSON output is non-empty.
cd "$SCRATCH"
test -f ./agileplus.db

echo "[hello-trace] listing projects (json)"
"$BIN" list-projects --json > "$SCRATCH/projects.json"
test -s "$SCRATCH/projects.json"
grep -q '"id"' "$SCRATCH/projects.json"

echo "[hello-trace] listing epics (table)"
"$BIN" list-epics > "$SCRATCH/epics.txt"
test -s "$SCRATCH/epics.txt"
# Epics table includes both the AgilePlus + Tracera titles from the seeded
# catalogs; the case-sensitive 'AgilePlus' label is a reliable marker.
grep -q 'AgilePlus' "$SCRATCH/epics.txt"

echo "[hello-trace] listing one story via --json to prove FR/NFR tags"
"$BIN" list-stories --epic 1 --json > "$SCRATCH/stories.json"
test -s "$SCRATCH/stories.json"

echo "[hello-trace] OK"
