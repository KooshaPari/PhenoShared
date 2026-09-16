#!/usr/bin/env bash
# scripts/cron/lint_branches_cron.sh — weekly branch-lint cron wrapper.
#
# Runs scripts/lint_branches.py against a list of repos (default:
# pheno-harness). Logs violations to bench/results/branch-lint/<date>.log
# so the SOTA snapshotter can pick up the trend.
#
# ADR 0008 §D2 — part of repository-ecosystem unification.
# Companion docs:
#   - docs/ECOSYSTEM.md §3       (taxonomy reference)
#   - scripts/lint_branches.py   (the linter)
#   - scripts/cron/README.md     (cron integration guide)

set -euo pipefail

# Resolve script-owned paths (CWD-invariant; this script may be invoked
# from cron, from a sibling-dir, or from a Makefile target).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PHENO_HARNESS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LINTER="$PHENO_HARNESS_ROOT/scripts/lint_branches.py"

# Repos to lint, in lint order. Each entry is a sibling-repo name (the
# linter resolves it via its bare-name lookup against the sibling-repos
# dir) or an absolute path.
REPOS=(
    "${REPO_PHENO:-pheno-harness}"
    "${REPO_OMNI:-OmniRoute}"
    "${REPO_AIRLOCK:-airlock}"
    "${REPO_AIRLOCK_V2:-airlock-v2}"
    "${REPO_PHENOAI:-phenoAI}"
)

# Where to write logs. Default: <pheno-harness>/bench/results/branch-lint/<UTC-date>/
# Resolved against PHENO_HARNESS_ROOT so the cron wrapper is CWD-invariant.
LOG_ROOT="${BRANCHLINT_LOG_ROOT:-$PHENO_HARNESS_ROOT/bench/results/branch-lint}"
LOG_DATE="${BRANCHLINT_LOG_DATE:-$(date -u +%Y-%m-%d)}"
LOG_DIR="$LOG_ROOT/$LOG_DATE"
mkdir -p "$LOG_DIR"

EXIT_TOTAL=0
SUMMARY="$LOG_DIR/summary.txt"
: > "$SUMMARY"

for repo in "${REPOS[@]}"; do
    echo "=== $repo ===" | tee -a "$SUMMARY"
    if ! python3 "$LINTER" "$repo" --json \
            > "$LOG_DIR/${repo//\//_}.json" 2> "$LOG_DIR/${repo//\//_}.err"; then
        # python returned non-zero (i.e. violations found)
        EXIT_TOTAL=$((EXIT_TOTAL + 1))
        # Re-run for human-readable text log
        python3 "$LINTER" "$repo" \
            > "$LOG_DIR/${repo//\//_}.txt" 2>&1 || true
    else
        echo "  (clean)" >> "$SUMMARY"
    fi
done

echo "" | tee -a "$SUMMARY"
echo "repos_with_violations=$EXIT_TOTAL / ${#REPOS[@]}" | tee -a "$SUMMARY"
echo "logs: $LOG_DIR" | tee -a "$SUMMARY"

# Cron exits 0 always (the inner linter already logged the violation
# counts; cron should not page on every branch rename that hasn't
# happened yet). Set BRANCHLINT_STRICT=1 to fail the cron on violations.
if [ "${BRANCHLINT_STRICT:-0}" = "1" ]; then
    exit "$EXIT_TOTAL"
fi
exit 0