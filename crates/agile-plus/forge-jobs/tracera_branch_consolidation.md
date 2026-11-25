REPO: E:/Dev/Tracera
TASK: Branch consolidation audit for Tracera. DO NOT commit anything.

The repo has ~50 local branches. Our goal is to consolidate all to integration/consolidate.

1. git branch -a | head -60  (list all branches)
2. git log --oneline main..HEAD (check if currently on main or a branch)
3. git branch --show-current
4. For each non-main branch (up to 10), check:
   - git log --oneline main..<branch> | wc -l  (how many commits ahead)
   - git diff --name-status main..<branch> | grep "^D" | wc -l  (deletion count = wipe risk)
5. Identify branches that are:
   a. SAFE to FF-merge (0 deletions, ≥1 commit)
   b. RISKY (has deletions, needs review)
   c. STALE (0 commits ahead of main)
6. Check if integration/consolidate branch exists: git branch -a | grep integration/consolidate
7. Write findings to /tmp/tracera-branch-audit-2026-06-15.md with columns:
   branch | commits_ahead | deletions | verdict

Report all verdicts.
