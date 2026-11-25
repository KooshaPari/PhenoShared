REPO: C:/Users/koosh/Dev/AgilePlus
TASK: Sweep ALL tracked files for missing EOF newlines and fix them.

The pre-commit "end-of-file-fixer" hook keeps failing. Fix this permanently.

1. Run: git ls-files | head -200 | while read f; do [ -f "$f" ] && python3 -c "import sys; c=open('$f','rb').read(); sys.exit(0 if not c or c.endswith(b'\n') else 1)" || echo "NEEDS_FIX: $f"; done
2. For each NEEDS_FIX file: append a newline (echo "" >> "$f" in bash, or use python open+write)
3. Also check ALL .md files, .json files, .yaml files, .toml files, .rs files in crates/
4. After fixing, do: git add -A && git commit -m "style: fix missing EOF newlines (pre-commit end-of-file-fixer sweep)"
5. Report total count fixed

RULES:
- No git stash. No force-push. No push to main. No worktrees.
- Actually DO the work. Report real counts.
- Working dir: C:/Users/koosh/Dev/AgilePlus
- Branch: integration/consolidate (already checked out)
