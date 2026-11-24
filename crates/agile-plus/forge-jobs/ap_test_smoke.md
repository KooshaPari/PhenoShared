# AgilePlus — smoke tests for 0-test crates

You are a forge agent working in the AgilePlus Rust workspace at C:/Users/koosh/Dev/AgilePlus.
PIPELINE lane (mutating): add tests → build → commit.

## Setup
```
cd C:/Users/koosh/Dev/AgilePlus
git fetch origin
git checkout integration/consolidate
git pull origin integration/consolidate
# Clone phenoShared sibling (required for workspace build)
cd ..
git clone --depth 1 https://github.com/KooshaPari/phenoShared.git phenoShared 2>/dev/null || true
cd AgilePlus
```

## Task
Add basic smoke tests (`#[test]`) to the crates currently having ZERO tests.
Identify them:
```
for crate in crates/*/; do
  count=$(grep -r '#\[test\]' "$crate/src" 2>/dev/null | wc -l)
  echo "$count $crate"
done | sort -n | head -15
```

For each 0-test crate (skip benches/fixtures/contract-tests/integration-tests):
- Add a `#[cfg(test)] mod tests { ... }` block in `src/lib.rs`
- Add 1-3 meaningful tests: constructor succeeds, round-trip, or basic invariant
- Tests must compile and pass: `cargo test -p <crate_name> 2>&1 | tail -5`

Priority crates (add tests to at least 5):
- agileplus-config
- agileplus-governance  
- agileplus-cache
- agileplus-telemetry
- agileplus-triage

## Build verify
```
CARGO_TARGET_DIR=C:/agileplus-target cargo test --workspace 2>&1 | tail -20
```

## Commit
```
git add crates/*/src/lib.rs
git commit -m "test: add smoke tests for 0-coverage crates (config/governance/cache/telemetry/triage)"
git push origin integration/consolidate
```

Report: crates covered, test count added, pass/fail summary.
