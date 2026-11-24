REPO: E:/Dev/Tracera
TASK: Consolidate SAFE branches into integration/consolidate. Read-only analysis first, then merge only verified-safe branches.

SAFE branches to evaluate (0 or few deletions):
- fix/main-ci-greenup (11 commits ahead, 0 deletions)
- fix/quick-wins-batch1 (5 commits ahead, 0 deletions)
- triage/stabilization-qol-219-218-222 (3 commits ahead, 0 deletions)
- wip/preserve-2026-06-05 (1 commit ahead, 0 deletions)

PROCEDURE for each branch:
1. ANTI-WIPE CHECK: git diff --name-status main..<branch> | grep "^D" | wc -l
   - If result == 0: SAFE, proceed
   - If result > 0: SKIP, report as RISKY
2. git checkout integration/consolidate
3. git merge --ff-only <branch> 2>/dev/null || git merge --no-ff <branch> -m "chore(consolidate): merge <branch> into integration/consolidate"
4. Report: merged/skipped/error per branch

After all merges:
5. git log --oneline integration/consolidate ^main | head -10
6. git push origin integration/consolidate

HARD RULES:
- NEVER push to main
- NEVER git stash
- NEVER --squash
- Anti-wipe gate REQUIRED before every merge (0 deletions only)
- FF-merge preferred (--ff-only), fallback --no-ff, NEVER --squash
- If any merge fails: continue to next branch, report failure
