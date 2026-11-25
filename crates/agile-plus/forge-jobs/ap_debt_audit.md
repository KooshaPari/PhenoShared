REPO: C:/Users/koosh/Dev/AgilePlus
TASK: Read-only debt hotspot audit. DO NOT commit anything.

1. Find all TODO/FIXME/HACK/UNWRAP comments:
   grep -rn "TODO\|FIXME\|HACK\|\.unwrap()" crates/ --include="*.rs" | grep -v "target/" | wc -l
2. List top 10 files by unwrap count:
   grep -rn "\.unwrap()" crates/ --include="*.rs" | grep -v "target/" | awk -F: '{print $1}' | sort | uniq -c | sort -rn | head -10
3. List all crates with 0 test functions:
   for d in crates/*/; do count=$(grep -r "#\[test\]" "$d/src" 2>/dev/null | wc -l); echo "$count $d"; done | sort -n | head -10
4. Check for any missing FR-AGP traceability comments:
   grep -rn "FR-AGP" crates/ --include="*.rs" | grep -v "target/" | awk -F: '{print $1}' | sort -u
5. Write findings to: docs/audit/debt-hotspots-2026-06-15.md (create dirs if needed)
   Format: ## Unwrap Count, ## TODO/FIXME Count, ## Untested Crates, ## FR Coverage

Report file path when done.
