#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  repo-duplicate-workflow.sh <canonical_repo_path> <duplicate_repo_path> [branch]

Purpose:
  - Validate duplicate repo state against canonical.
  - Ensure duplicate has no unique commits not on canonical.
  - Emit a safe decision: KEEP/MERGE/ARCHIVE.

Examples:
  ./repo-duplicate-workflow.sh ~/CodeProjects/Phenotype/repos/heliosCLI ~/CodeProjects/Phenotype/repos/helios-cli feature/helios-rebrand
USAGE
}

if [[ $# -lt 2 ]]; then
  usage
  exit 1
fi

CANONICAL="${1%/}"
DUP="${2%/}"
BRANCH="${3:-feature/helios-rebrand}"

if [[ ! -d "$CANONICAL/.git" || ! -d "$DUP/.git" ]]; then
  echo "Both paths must be valid git checkouts."
  exit 1
fi

cd "$CANONICAL"
echo "== [$CANONICAL] canonical baseline check =="
git fetch --all --prune || {
  echo "WARN: canonical fetch failed (continuing with local refs)."
}

CANONICAL_HEAD=$(git rev-parse "$BRANCH")
echo "Canonical HEAD: $CANONICAL_HEAD"

cd "$DUP"
echo "== [$DUP] sync + compare against canonical =="
git fetch --all --prune || {
  echo "WARN: duplicate fetch failed (continuing with available local refs)."
}
git remote add canonical "$CANONICAL" 2>/dev/null || true
git fetch canonical --prune || {
  echo "WARN: canonical mirror fetch failed."
}

if ! git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  CANONICAL_REF="origin/$BRANCH"
  echo "Duplicate does not have local branch $BRANCH."
  echo "Run: git -C \"$DUP\" checkout -B \"$BRANCH\" \"$CANONICAL_REF\""
  exit 1
fi

CANONICAL_REF="canonical/$BRANCH"
if ! git show-ref --verify --quiet "refs/remotes/$CANONICAL_REF"; then
  echo "Canonical remote branch not found at $CANONICAL_REF"
  exit 1
fi

read -r CANONICAL_AHEAD DUP_AHEAD < <(
  git rev-list --left-right --count "${CANONICAL_REF}".."$BRANCH"
)
echo "Delta (canonical..duplicate): $CANONICAL_AHEAD | $DUP_AHEAD"

if [[ "$CANONICAL_AHEAD" -eq 0 && "$DUP_AHEAD" -eq 0 ]]; then
  echo "STATUS: ALIGNED"
else
  echo "STATUS: DIVERGED"
  echo "-- Commits only in canonical:"
  git log --left-right --no-merges --oneline "canonical/$BRANCH...$BRANCH" | sed -n '1,80p'
fi

cd "$DUP"
UNCOMMITTED=$(git status --porcelain)
if [[ -n "$UNCOMMITTED" ]]; then
  echo "UNCOMMITTED CHANGES in duplicate:"
  git status --short
  echo "Decision:"
  echo "  - Review and export if needed before delete."
else
  echo "UNCOMMITTED CHANGES: none"
fi

echo "Recommended deletion command (if no local value):"
echo "  rm -rf \"$DUP\""
