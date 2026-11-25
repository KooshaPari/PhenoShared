REPO: C:/Users/koosh/Dev/AgilePlus
TASK: Find and fix broken internal markdown doc links.

The "Doc Links" CI job is failing. Fix broken internal links in markdown files.

1. List all .md files: find . -name "*.md" -not -path "./.git/*" -not -path "./target/*" | head -60
2. For each .md file, grep for [text](path) style links where path does NOT start with http
3. For relative links, check if the target file exists
4. Fix broken links (update paths or remove dead references)
5. Also check .github/workflows/ for any referenced file paths that don't exist
6. Run: cat .github/workflows/doc-links.yml 2>/dev/null || find .github/workflows -name "*.yml" | xargs grep -l "markdown\|link\|doc" 2>/dev/null
7. Commit any fixes: git add -A && git commit -m "docs: fix broken markdown links"

RULES:
- No git stash. No force-push. No push to main. No worktrees.
- Actually DO the work. Report counts of fixed vs remaining broken links.
- Working dir: C:/Users/koosh/Dev/AgilePlus
- Branch: integration/consolidate (already checked out)
