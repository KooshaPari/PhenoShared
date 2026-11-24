REPO: C:/Users/koosh/Dev/AgilePlus
TASK: Audit and fix broken markdown doc links.

1. Run: find . -name "*.md" -not -path "./.git/*" | head -50 | xargs grep -l "\[.*\](.*)" 2>/dev/null | head -20
2. For each .md file found, identify links with patterns like [text](path) that reference .md files or local paths
3. Check if target files exist: for relative paths, verify they exist on disk
4. Fix any broken internal links (rename paths, update references)
5. Do NOT fix external http:// or https:// links
6. Commit any fixes: git add -A && git commit -m "docs: fix broken internal markdown links"
7. Report: list broken links found, which were fixed, which remain (if any require manual intervention)

RULES:
- No git stash. No force-push. No push to main. No worktrees.
- Actually DO the work with your tools. Report real output counts.
- Working dir: C:/Users/koosh/Dev/AgilePlus
- Branch: integration/consolidate (already checked out)
