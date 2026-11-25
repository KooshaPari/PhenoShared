#!/bin/bash
BASE="integration/consolidate"

echo "=== BRANCH TRIAGE vs $BASE ==="
echo ""

# Collect results into arrays
declare -a BRANCHES=()
declare -a AHEADS=()
declare -a DELS=()
declare -a STATUSES=()

while IFS= read -r branch; do
  [ -z "$branch" ] && continue

  ahead=$(git rev-list --count "$BASE..$branch" 2>/dev/null || echo "0")
  dels=$(git diff --name-status "$BASE...$branch" 2>/dev/null | grep -c "^D" || echo "0")

  if [ "$ahead" -gt 0 ] && [ "$dels" -eq 0 ]; then
    status="MERGE-READY"
  elif [ "$dels" -gt 0 ]; then
    status="SKIP-DEL"
  else
    status="ALREADY-MERGED"
  fi

  BRANCHES+=("$branch")
  AHEADS+=("$ahead")
  DELS+=("$dels")
  STATUSES+=("$status")
done < _branches.txt

# Print table
printf "| %-45s | %-13s | %-11s | %-15s |\n" "branch" "commits_ahead" "deletions" "status"
printf "| %-45s | %-13s | %-11s | %-15s |\n" "---------------------------------------------" "-------------" "-----------" "---------------"
for i in "${!BRANCHES[@]}"; do
  printf "| %-45s | %-13s | %-11s | %-15s |\n" "${BRANCHES[$i]}" "${AHEADS[$i]}" "${DELS[$i]}" "${STATUSES[$i]}"
done

echo ""
echo "=== MERGE-READY branches: commit subjects ==="
echo ""

for i in "${!BRANCHES[@]}"; do
  if [ "${STATUSES[$i]}" = "MERGE-READY" ]; then
    echo "--- ${BRANCHES[$i]} (${AHEADS[$i]} commits, ${DELS[$i]} deletions) ---"
    git log --oneline "$BASE..${BRANCHES[$i]}"
    echo ""
  fi
done
