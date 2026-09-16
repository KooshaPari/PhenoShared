#!/usr/bin/env bash
# scripts/cron/health_repo_cron.sh — multi-repo weekly health probe cron wrapper.
#
# Companion to scripts/health_repo.sh.  CWD-invariant: resolves the script
# directory up-front so it can be invoked from any cwd (LaunchAgents in
# particular run from $HOME by default).
#
# Writes to bench/results/health_repo/<YYYY-MM-DD>/<repo>.log + <repo>.err.
# Both files are gitignored by the bench/results/**/*.json policy; .log and
# .err are not gitignored but are tracked as debug artefacts (small enough).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HEALTH_REPO_SH="$SCRIPT_DIR/../health_repo.sh"

# Sibling repos to probe weekly.  Add new entries here as the family grows.
REPOS=(
    pheno-harness
    airlock
    OmniRoute
    thegent
    sharecli
    forgecode
    cliproxyapi-plusplus
)

DATE_TAG="${HEALTH_REPO_DATE_TAG:-$(date -u +%Y-%m-%d)}"

echo "=== health_repo cron @ $DATE_TAG ==="
for repo in "${REPOS[@]}"; do
    if [ -d "$HOME/CodeProjects/Phenotype/repos/$repo" ]; then
        echo "--- probing $repo ---"
        cd "$HOME/CodeProjects/Phenotype/repos/$repo"
        if [ -x "$HEALTH_REPO_SH" ]; then
            bash "$HEALTH_REPO_SH" || true
        fi
    fi
done

echo "=== health_repo cron done ==="
