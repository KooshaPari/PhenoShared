# AgilePlus — unwrap() → expect()/? reduction sweep

You are a forge agent working in the AgilePlus Rust workspace at C:/Users/koosh/Dev/AgilePlus.
This is a PIPELINE lane (mutating): build → fix → test → commit.

## Setup
```
cd C:/Users/koosh/Dev/AgilePlus
git fetch origin
git checkout integration/consolidate
git pull origin integration/consolidate
```

## Task
Reduce `unwrap()` calls to safe alternatives. Priority targets:
1. `crates/agileplus-sqlite/src/lib.rs` (~295 unwraps reported)
2. `crates/agileplus-dashboard/src/routes.rs` (high count)

Rules:
- `unwrap()` on `Option` at a boundary that CAN fail → convert to `ok_or_else(|| anyhow::anyhow!("..."))?`
- `unwrap()` in test code → leave as-is (tests should panic on bad data)
- `unwrap()` in bench helpers → leave as-is
- `unwrap()` where value is mathematically guaranteed → convert to `expect("reason")`
- Do NOT change any logic, only the error propagation
- RUSTFLAGS="-D warnings" applies — no new warnings

## Build verify
```
cd C:/Users/koosh/Dev/AgilePlus
CARGO_TARGET_DIR=C:/agileplus-target cargo clippy --workspace 2>&1 | grep -c "^error" || true
```
Target: 0 errors. If clippy errors remain, fix them before committing.

## Commit
```
git add -p  # only changed files
git commit -m "fix: reduce unwrap() to expect/? in sqlite and dashboard crates"
git push origin integration/consolidate
```

## Anti-wipe gate (MANDATORY before any merge)
```
git diff --name-status HEAD^..HEAD | grep -c '^D' 
```
If >0 deletions, ABORT and report.

## Report
Output:
- Count of unwrap() converted (before/after per crate)
- Final clippy error count
- git push result
