# Testing

Portable tests: full generated YAML snapshot, exact guard structure, handwritten trigger/concurrency/Linux runner policy assertions.

Unix-only semantic tests substitute static fixture context into actual serialized expressions and evaluate the shared boolean subset with Bash. Unrelated events cover 2 actions x 4 labels x 2 opt-in states x 5 jobs. Ordinary/relevant cases cover 10 scenarios x 5 jobs. This is synthetic, not hosted Actions validation.

Planned gates: crate cargo insta test --accept, check, clippy, scoped rustfmt check, actionlint ci.yml. Regenerate only ci.yml; full suite uses CI=true to prevent unrelated workflow writes.

## Observed results

- `cargo test -p forge_ci --test ci generate -- --exact`: passed, regenerated ci.yml only.
- `CI=true cargo insta test -p forge_ci --accept`: 18 tests passed across 2 binaries, 0 skipped.
- `CI=true cargo check -p forge_ci`: passed.
- `CI=true cargo clippy -p forge_ci --all-targets -- -D warnings`: passed.
- `rustfmt --edition 2024 --check crates/forge_ci/src/workflows/ci.rs`: passed.
- `actionlint .github/workflows/ci.yml`: passed.
- Scoped `git diff --check`: passed.

No hosted jobs or paid runners were executed.

## Observed results

- `cargo test -p forge_ci --test ci generate -- --exact`: passed, regenerated ci.yml only.
- `CI=true cargo insta test -p forge_ci --accept`: 18 tests passed across 2 binaries, 0 skipped. Existing YAML is the snapshot fixture; no insta snapshots to review.
- `CI=true cargo check -p forge_ci`: passed.
- `CI=true cargo clippy -p forge_ci --all-targets -- -D warnings`: passed.
- `rustfmt --edition 2024 --check crates/forge_ci/src/workflows/ci.rs`: passed.
- `actionlint .github/workflows/ci.yml`: passed.
- Scoped `git diff --check`: passed.

Initial cold-compilation focused-test command timed out after 600 seconds with two portable tests already passed. The final full crate run supersedes that partial attempt and passes both semantic tests. No hosted jobs or paid runners were executed.
