# AgilePlus — FR/NFR traceability gap audit

READ-ONLY lane. Do NOT run cargo or git write commands. Write findings to docs/audit/fr_traceability_gaps.md.

## Setup
```
cd C:/Users/koosh/Dev/AgilePlus
```

## Task
Map FR-AGP requirement IDs to implementing code and test coverage.

1. List all FR-AGP IDs referenced in the codebase:
```
grep -r 'FR-AGP' crates/ --include='*.rs' -h | grep -oP 'FR-AGP-\d+' | sort -u
```

2. For each FR-AGP ID found:
   - Which crates/files reference it
   - Is there a test that validates it (search for the ID in test files)
   - Is there a struct/function that implements it

3. Check docs/requirements/ for any FR spec files:
```
ls docs/requirements/ 2>/dev/null || echo "no requirements dir"
find . -name "*.md" | xargs grep -l "FR-AGP" 2>/dev/null | head -20
```

4. Identify gaps:
   - FRs with code but no tests
   - FRs in docs but not in code
   - FRs in code but not in docs

Write a full gap matrix to docs/audit/fr_traceability_gaps.md:
| FR-AGP-ID | Impl Crate | Has Test? | Doc Reference | Gap? |
|-----------|------------|-----------|---------------|------|

## Output
Create the file docs/audit/fr_traceability_gaps.md with the full matrix.
Then: `git add docs/audit/fr_traceability_gaps.md && git commit -m "docs: FR-AGP traceability gap matrix" && git push origin integration/consolidate`
