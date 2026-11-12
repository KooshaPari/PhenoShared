#!/usr/bin/env bash
# Regenerates absorption/STATE.md from the trees on disk. Every field is derived,
# never asserted: remote from `git remote -v`, SHA from `git log -1`, and
# absorbed/in-progress from `git merge-base --is-ancestor <sha> origin/main`.
# A tree with no .git, no remote, or no commit is UNKNOWN, not "absorbed".
set -u
cd "$(dirname "$0")/.."
MAIN_SHA=$(git rev-parse --short origin/main 2>/dev/null || echo UNKNOWN)
echo "# Absorption Ledger"
echo
echo "Derived by \`absorption/state.sh\`. Base: \`origin/main @ ${MAIN_SHA}\`."
echo "Status rule: \`absorbed\` = the tree's HEAD commit is an ancestor of origin/main;"
echo "\`in-progress\` = a git tree whose HEAD is not reachable from origin/main;"
echo "\`unexamined\` = no \`.git\` in the tree, so no lineage can be derived."
echo
echo "| Tree | Upstream remote | HEAD SHA | Status |"
echo "|---|---|---|---|"
for d in absorption/*/; do
  d=${d%/}
  if [ ! -e "$d/.git" ]; then
    echo "| \`$d\` | UNKNOWN (not a git tree) | UNKNOWN | unexamined |"
    continue
  fi
  remote=$(git -C "$d" remote get-url origin 2>/dev/null || echo UNKNOWN)
  [ -z "$remote" ] && remote="UNKNOWN (no origin)"
  sha=$(git -C "$d" log -1 --format=%h 2>/dev/null || echo UNKNOWN)
  [ -z "$sha" ] && sha=UNKNOWN
  if [ "$sha" = UNKNOWN ]; then
    status="unexamined"
  elif git -C "$d" merge-base --is-ancestor "$sha" origin/main 2>/dev/null; then
    status="absorbed"
  else
    status="in-progress"
  fi
  echo "| \`$d\` | \`$remote\` | $sha | $status |"
done
