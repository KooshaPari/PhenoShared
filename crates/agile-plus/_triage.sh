#!/bin/bash
BASE="integration/consolidate"

echo "=== BRANCH TRIAGE vs $BASE ==="
echo ""
printf "| %-45s | %-13s | %-11s | %-10s |\n" "branch" "commits_ahead" "deletions" "status"
printf "| %-45s | %-13s | %-11s | %-10s |\n" "---------------------------------------------" "-------------" "-----------" "----------"

git branch | grep -v "integration/consolidate\|^\*" | while read -r branch; do
  branch=$(echo "$branch" | tr -d '[:space:]')
  [ -z "$branch" ] && continue

  ahead=$(git rev-list --count "$BASE..$branch" 2>/dev/null)
  dels=$(git diff --name-status "$BASE...$branch" 2>/dev/null | grep -c "^D")

  if [ "$ahead" -gt 0 ] && [ "$dels" -eq 0 ]; then
    status="MERGE-READY"
  elif [ "$dels" -gt 0 ]; then
    status="SKIP-DEL"
  else
    status="ALREADY-MERGED"
  fi

  printf "| %-45s | %-13s | %-11s | %-10s |\n" "$branch" "$ahead" "$dels" "$status"
done

echo ""
echo "=== MERGE-READY BRANCHES: commit subjects ==="
echo ""

git branch | grep -v "integration/consolidate\|^\*" | while read -r branch; do
  branch=$(echo "$branch" | tr -d '[:space:]')
  [ -z "$branch" ] && continue

  ahead=$(git rev-list --count "$BASE..$branch" 2>/dev/null)
  dels=$(git diff --name-status "$BASE...$branch" 2>/dev/null | grep -c "^D")

  if [ "$ahead" -gt 0 ] && [ "$dels" -eq 0 ]; then
    echo "--- $branch ($ahead commits, $dels deletions) ---"
    git log --oneline "$BASE..$branch"
    echo ""
  fi
done
