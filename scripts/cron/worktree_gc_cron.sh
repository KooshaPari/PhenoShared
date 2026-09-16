#!/usr/bin/env bash
# scripts/cron/worktree_gc_cron.sh — weekly worktree GC cron wrapper.
#
# Companion to scripts/cron/worktree_gc.sh.  CWD-invariant: resolves all
# paths against the pheno-harness repo root so the wrapper can be invoked
# from any cwd (LaunchAgents run from $HOME by default).
#
# Runs in DRY-RUN mode by default — set GC_APPLY=1 to actually prune.
# Reclaims prunable worktrees and gone branches across the repo family.
#
# Writes to bench/results/gc/<YYYY-MM-DD>/<repo>.log.  The .log files are
# small and tracked as debug artefacts (the actual worktree state lives
# in git, so we only need the logs as evidence the cron ran).

set -euo pipefail

# Resolve pheno-harness root from this script's location, not cwd.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PHENO_HARNESS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GC_SH="$SCRIPT_DIR/worktree_gc.sh"

# Default repos (override with WORKTREE_GC_REPOS="repo1 repo2 ...")
DEFAULT_REPOS=(pheno-harness airlock OmniRoute thegent)

# Allow override via env (space-separated list).
if [ -n "${WORKTREE_GC_REPOS:-}" ]; then
    REPOS=( ${WORKTREE_GC_REPOS} )
else
    REPOS=( "${DEFAULT_REPOS[@]}" )
fi

DATE_TAG="${WORKTREE_GC_DATE_TAG:-$(date -u +%Y-%m-%d)}"
APPLY_FLAG="${GC_APPLY:-0}"
LOG_ROOT="$PHENO_HARNESS_ROOT/bench/results/gc"
LOG_DIR="$LOG_ROOT/$DATE_TAG"

mkdir -p "$LOG_DIR"

MODE="dry-run"
if [ "$APPLY_FLAG" = "1" ]; then
    MODE="apply"
fi

echo "=== worktree_gc cron ($MODE) @ $DATE_TAG ==="
echo "    pheno-harness root: $PHENO_HARNESS_ROOT"
echo "    log dir:            $LOG_DIR"
echo "    repos:              ${REPOS[*]}"

for repo in "${REPOS[@]}"; do
    REPO_PATH="$HOME/CodeProjects/Phenotype/repos/$repo"
    LOG_FILE="$LOG_DIR/$repo.log"
    echo "--- probing $repo ---"
    if [ ! -d "$REPO_PATH/.git" ] && [ ! -f "$REPO_PATH/.git" ]; then
        echo "[skip] $repo not a git repo at $REPO_PATH" | tee -a "$LOG_FILE"
        continue
    fi
    (
        cd "$REPO_PATH"
        if [ "$APPLY_FLAG" = "1" ]; then
            bash "$GC_SH" --apply "$repo" || true
        else
            bash "$GC_SH" "$repo" || true
        fi
    ) > "$LOG_FILE" 2>&1
    echo "    log: $LOG_FILE ($(wc -l < "$LOG_FILE") lines)"
done

echo "=== worktree_gc cron done ==="
