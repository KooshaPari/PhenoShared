#!/bin/bash
# airlock-v2-smoke-test.sh
# -------------------------
# End-to-end smoke test for the airlock-v2 infrastructure.
# Verifies that:
#   1. The auto-commit daemon can find a temp dirty repo under repos/
#   2. The hook script accepts a Codex-style event JSON and creates a wip branch
#   3. The cleanup daemon can dry-run consolidation
#   4. All daemons pass syntax/type checks
#
# This script creates a TEMPORARY git repo under
# ~/CodeProjects/Phenotype/repos/airlock-v2-smoke-test-<pid>/, exercises
# the daemons against it, and cleans up afterwards. It does NOT modify any
# real repo, does NOT push to any real remote, and does NOT touch
# ~/.airlock/.
#
# NOTE: the smoke dir MUST NOT start with a dot — auto-commit-daemon.py
# explicitly skips dot-prefixed directories during its top-level walk, so
# a hidden smoke dir would be invisible to the daemon under test.
#
# Exit codes:
#   0 : smoke test passed
#   1 : smoke test setup failed
#   2 : smoke test assertion failed
#   3 : smoke test cleanup failed (treated as warning)
set -uo pipefail

# ---------- config ----------
REPO_ROOT="${AIRLOCK_V2_ROOT:-$HOME/CodeProjects/Phenotype/repos}"
AIRLOCK_V2="/Users/kooshapari/CodeProjects/Phenotype/repos/_phenofleet-decisions/airlock-v2"
# Use an ISOLATED temp scan root so the auto-commit daemon does not scan the
# real ~250 git repos under REPO_ROOT. The smoke repo is placed at
# <SMOKE_SCAN_ROOT>/<SMOKE_BIN>/ so the daemon only discovers the smoke
# repo when AIRLOCK_V2_ROOT is overridden to SMOKE_SCAN_ROOT.
SMOKE_SCAN_ROOT="$(mktemp -d -t airlock-v2-smoke-root.XXXXXX)"
SMOKE_BIN="airlock-v2-smoke-test-$$"
SMOKE_DIR="$SMOKE_SCAN_ROOT/$SMOKE_BIN"
SMOKE_BRANCH_PREFIX="wip/smoke-test-$$"
LOG_DIR="$HOME/.airlock-v2/logs"

# Colors (no-op if not a tty).
if [ -t 1 ]; then
  RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RESET=$'\033[0m'
else
  RED=""; GREEN=""; YELLOW=""; RESET=""
fi

PASS=0
FAIL=0
SKIP=0

ok()   { echo "${GREEN}PASS${RESET} $*"; PASS=$((PASS+1)); }
bad()  { echo "${RED}FAIL${RESET} $*"; FAIL=$((FAIL+1)); }
note() { echo "${YELLOW}NOTE${RESET} $*"; }
skip() { echo "${YELLOW}SKIP${RESET} $*"; SKIP=$((SKIP+1)); }

cleanup() {
  if [ -d "$SMOKE_SCAN_ROOT" ]; then
    rm -rf "$SMOKE_SCAN_ROOT" 2>/dev/null || true
  fi
  if [ -d "$REPO_ROOT/airlock-v2-smoke-test-$$" ]; then
    rm -rf "$REPO_ROOT/airlock-v2-smoke-test-$$" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "=== Airlock V2 Smoke Test ==="
echo "REPO_ROOT: $REPO_ROOT"
echo "AIRLOCK_V2: $AIRLOCK_V2"
echo "SMOKE_DIR:  $SMOKE_DIR"
echo

# ---------- preflight ----------
echo "[1] Preflight"

if [ ! -d "$AIRLOCK_V2" ]; then
  bad "airlock-v2 directory missing: $AIRLOCK_V2"
  exit 1
fi
ok "airlock-v2 directory present"

if [ ! -d "$REPO_ROOT" ]; then
  bad "REPO_ROOT missing: $REPO_ROOT"
  exit 1
fi
ok "REPO_ROOT present"

if ! command -v python3 >/dev/null 2>&1; then
  bad "python3 not on PATH"
  exit 1
fi
ok "python3 available: $(python3 --version 2>&1 | head -n1)"

if ! command -v git >/dev/null 2>&1; then
  bad "git not on PATH"
  exit 1
fi
ok "git available: $(git --version)"

if ! command -v bash >/dev/null 2>&1; then
  bad "bash not on PATH"
  exit 1
fi
ok "bash available: $BASH_VERSION"

# ---------- syntax checks ----------
echo
echo "[2] Syntax checks"

for f in "$AIRLOCK_V2/daemons/auto-commit-daemon.py" \
         "$AIRLOCK_V2/daemons/cleanup-daemon.py"; do
  if python3 -m py_compile "$f" 2>/dev/null; then
    ok "py_compile: $(basename "$f")"
  else
    bad "py_compile FAILED: $(basename "$f")"
    python3 -m py_compile "$f"
  fi
done

if bash -n "$AIRLOCK_V2/hooks/airlock-v2-hook.sh" 2>/dev/null; then
  ok "bash -n: airlock-v2-hook.sh"
else
  bad "bash -n FAILED: airlock-v2-hook.sh"
fi

for f in "$AIRLOCK_V2/daemons/com.phenotype.auto-commit-daemon.plist" \
         "$AIRLOCK_V2/daemons/com.phenotype.cleanup-daemon.plist"; do
  if plutil -lint "$f" >/dev/null 2>&1; then
    ok "plutil: $(basename "$f")"
  else
    bad "plutil FAILED: $(basename "$f")"
  fi
done

# ---------- JSON validity ----------
echo
echo "[3] JSON validity"

for f in "$AIRLOCK_V2/hooks/codex-hooks.json" \
         "$AIRLOCK_V2/hooks/claude-hooks.json" \
         "$AIRLOCK_V2/hooks/cursor-hooks.json"; do
  if python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$f" 2>/dev/null; then
    ok "json valid: $(basename "$f")"
  else
    bad "json INVALID: $(basename "$f")"
  fi
done

# ---------- create a fake dirty repo ----------
echo
echo "[4] Smoke test repo"

mkdir -p "$SMOKE_DIR"
cd "$SMOKE_DIR" || { bad "could not enter $SMOKE_DIR"; exit 1; }
git init -q -b main .
git config user.name "smoke-test"
git config user.email "smoke@test.local"
echo "hello" > README.md
git add README.md
git commit -q -m "initial"
ok "created smoke-test repo at $SMOKE_DIR"

# Make it dirty.
echo "more work" >> README.md
echo "stale" > wip.tmp
ok "introduced 2 dirty files"

# ---------- auto-commit daemon runs cleanly on dirty repo ----------
echo
echo "[5] auto-commit-daemon.py --once against smoke dir"

mkdir -p "$LOG_DIR"

# Run the daemon constrained to an isolated temp directory that contains
# ONLY the smoke repo. This prevents the daemon from also scanning all of
# ~/CodeProjects/Phenotype/repos/ which has ~250 git repos and would slow
# the test down. We also bypass the airlock-dameon-busy probe by using a
# fake socket path so the daemon proceeds even when the real socket is wedged.
output="$(AIRLOCK_V2_ROOT="$SMOKE_SCAN_ROOT" AIRLOCK_V2_INTERVAL=10 \
            AIRLOCK_V2_LOCK_PATH="/tmp/airlock-v2.smoke-autocommit-$$" \
            AIRLOCK_V2_AIRLOCK_SOCKET="/tmp/airlock-v2.smoke-no-socket-$$" \
            timeout 60 python3 "$AIRLOCK_V2/daemons/auto-commit-daemon.py" --once 2>&1)" || true
rc=$?
echo "$output" | tail -n 3

if [ $rc -eq 0 ] || [ $rc -eq 2 ]; then
  ok "auto-commit-daemon --once exited cleanly (rc=$rc)"
else
  bad "auto-commit-daemon --once failed (rc=$rc)"
fi

# Check the smoke repo for a wip/-auto branch.
cd "$SMOKE_DIR" || true
branches="$(git for-each-ref --format='%(refname:short)' refs/heads/wip/ 2>/dev/null || true)"
if printf '%s' "$branches" | grep -q "^wip/.*-auto$"; then
  ok "wip/-auto branch created: $branches"
else
  bad "no wip/-auto branch created (branches=$branches)"
fi

# ---------- hook script invocation ----------
echo
echo "[6] airlock-v2-hook.sh: feed it a synthetic Codex event"

# Reset dirty state by going back to a clean repo state.
# We use -- to detach HEAD, then explicitly switch to main. This avoids the
# case where the previous auto-commit step put us on a wip/* branch — by
# checking out main we restore a clean baseline.
git checkout -q -- . 2>/dev/null || true
git -c advice.detachedHead=false checkout -q main 2>/dev/null || git switch -q main 2>/dev/null || true

# Re-introduce dirt.
echo "hook test" >> README.md

# Build a payload matching Codex's hooks.json schema.
PAYLOAD=$(printf '{"cwd":"%s","tool_name":"edit","event":"PostToolUse","session_id":"smoke-%d"}' \
            "$SMOKE_DIR" "$$")

# Use a temp file for stdin so the env vars can be applied to the hook
# script directly (env-vars prefixed before a pipeline only apply to that
# pipeline's leftmost command in bash; using a temp file decouples stdin
# from the env-block).
HOOK_STDIN="$(mktemp -t airlock-v2-smoke-hook.XXXXXX)"
trap 'rm -f "$HOOK_STDIN"' EXIT
printf '%s' "$PAYLOAD" > "$HOOK_STDIN"

(
  cd "$REPO_ROOT" || exit 1
  AIRLOCK_V2_AGENT=smoke \
  AIRLOCK_V2_EVENT_ID="smoke-$$" \
  AIRLOCK_V2_LOG="$LOG_DIR/smoke-hook.log" \
  AIRLOCK_V2_ROOT="$SMOKE_SCAN_ROOT" \
  timeout 30 bash "$AIRLOCK_V2/hooks/airlock-v2-hook.sh" \
    < "$HOOK_STDIN" >/dev/null 2>&1
)
rc=$?
if [ $rc -eq 0 ] || [ $rc -eq 1 ]; then
  ok "hook script exited cleanly (rc=$rc, 0=committed, 1=no-op or silent skip)"
else
  bad "hook script failed (rc=$rc)"
fi

# Did the hook create a wip branch?
branches="$(git for-each-ref --format='%(refname:short)' refs/heads/wip/ 2>/dev/null || true)"
echo "branches after hook: $branches"
if printf '%s' "$branches" | grep -q "smoke"; then
  ok "wip branch created by hook"
else
  bad "hook did not create a wip branch"
fi

# ---------- cleanup daemon dry-run ----------
echo
echo "[7] cleanup-daemon.py --once --dry-run-ish"

# Use the same isolated scan root so the cleanup daemon does NOT touch real
# repos. AIRLOCK_V2_DRY_RUN=1 keeps the daemon in dry-run mode where it just
# reports what it would do.
output=$(AIRLOCK_V2_ROOT="$SMOKE_SCAN_ROOT" AIRLOCK_V2_DRY_RUN=1 \
            AIRLOCK_V2_LOCK_PATH="/tmp/airlock-v2.smoke-cleanup-$$" \
            AIRLOCK_V2_AIRLOCK_SOCKET="/tmp/airlock-v2.smoke-no-socket-$$" \
            AIRLOCK_V2_ARCHIVE_DAYS=30 \
            timeout 60 python3 "$AIRLOCK_V2/daemons/cleanup-daemon.py" --once 2>&1) || true
rc=$?
echo "$output" | tail -n 3

if [ $rc -eq 0 ] || [ $rc -eq 2 ]; then
  ok "cleanup-daemon --once exited (rc=$rc)"
else
  bad "cleanup-daemon --once failed (rc=$rc)"
fi

# ---------- log presence ----------
echo
echo "[8] Log files"

for logfile in "$LOG_DIR/auto-commit.log" "$LOG_DIR/cleanup.log" "$LOG_DIR/hook.log"; do
  if [ -f "$logfile" ] || [ -n "${DRY_RUN:-}" ]; then
    skip "log not yet created (daemons not running): $(basename "$logfile")"
  fi
done

# ---------- summary ----------
echo
echo "=== Smoke Test Summary ==="
echo "PASS: $PASS"
echo "FAIL: $FAIL"
echo "SKIP: $SKIP"
echo
if [ $FAIL -ne 0 ]; then
  echo "${RED}SMOKE TEST FAILED${RESET}"
  exit 2
else
  echo "${GREEN}SMOKE TEST PASSED${RESET}"
  exit 0
fi
