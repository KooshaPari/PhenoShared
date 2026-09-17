REPO: C:/Users/koosh/Dev/AgilePlus
TASK: Find and fix ALL remaining clippy -D warnings lints across the workspace.

phenoShared sibling required:
git clone --depth 1 https://github.com/KooshaPari/phenoShared.git ../phenoShared 2>/dev/null || echo "already exists"

Then:
1. Run: cd rust && cargo clippy --workspace --all-targets -- -D warnings 2>&1 | grep "^error" | head -30
2. For each error found:
   - Read the file:line indicated
   - Apply the fix suggested by clippy (the help: line shows exactly what to do)
   - Common fixes: unnecessary_lazy_evaluations (or_else(||None)->or(None)), needless_range_loop, doc_lazy_continuation (add spaces), unnecessary_cast (remove `as T`), unused_imports (remove), clippy::map_unwrap_or etc
3. Run clippy again after fixes to verify clean
4. Commit: git add -A && git commit -m "fix(clippy): sweep all -D warnings lint errors across workspace"
5. Push: git push origin integration/consolidate

RULES:
- No git stash. No force-push. No push to main. No worktrees.
- Working dir: C:/Users/koosh/Dev/AgilePlus  
- Branch: integration/consolidate (already checked out)
- Run from rust/ subdir for cargo commands
- phenoShared MUST be cloned as ../phenoShared before cargo runs
