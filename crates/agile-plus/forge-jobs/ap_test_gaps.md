REPO: C:/Users/koosh/Dev/AgilePlus
TASK: Identify test gaps and write missing unit tests for agileplus-triage and agileplus-domain.

1. Run: cargo test --workspace --manifest-path rust/Cargo.toml 2>&1 | tail -30 (read-only, do not commit build artifacts)
2. If build fails, skip build and just read source files instead
3. Read: crates/agileplus-triage/src/claim.rs — identify public fns/structs that have NO #[test] coverage
4. Read: crates/agileplus-domain/src/domain/*.rs — identify untested state transitions
5. Write new #[cfg(test)] mod tests blocks IN THE SAME FILES covering:
   a. ClaimStore: claim/release/heartbeat/expire cycle
   b. Cycle state machine: invalid transitions (e.g. Archived -> Active)  
   c. Any pure functions missing tests
6. Commit: git add -A && git commit -m "test(triage,domain): add missing unit tests for claim store and cycle SM"
7. Report: which tests were added, test fn names

RULES:
- No git stash. No force-push. No push to main. No worktrees.
- phenoShared sibling: git clone --depth 1 https://github.com/KooshaPari/phenoShared.git ../phenoShared (if needed for build)
- Actually write the tests. Report real test names added.
- Working dir: C:/Users/koosh/Dev/AgilePlus
- Branch: integration/consolidate (already checked out)
