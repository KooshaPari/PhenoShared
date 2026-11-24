# CVP Pilot Task: Fix, Implement, and Document

## Objective

Run this exact task against the cvp-fixture repo using each coding agent (jcode, Codex, ForgeCode). Measure and compare their performance.

## Starting State

- Repo: `~/CodeProjects/cvp-fixture/`
- `cargo check` passes (2 warnings)
- `cargo test` fails: 13 pass, 1 fail (`test_take_filter` — wrong assertion)
- `DeduplicateFilter` is a no-op (TODO in code)
- Public types lack doc comments

## Task Instructions (give to agent verbatim)

```
Work in ~/CodeProjects/cvp-fixture/

1. Research the codebase structure and understand the pipeline library
2. Fix the failing test in pipeline/src/filters.rs (test_take_filter has wrong assertion)
3. Implement the DeduplicateFilter to remove items with duplicate keys (keep first occurrence)
4. Add doc comments to all public types and traits in pipeline/src/
5. Fix all compiler warnings (unused imports)
6. Run `cargo test` and ensure all tests pass
7. Run `cargo clippy` and fix any warnings
8. Commit your changes with a descriptive message
```

## Measurement Points

| Metric | How to measure |
|--------|---------------|
| Total time | Wall clock from task start to final commit |
| Tool calls | Count of tool invocations (bash, read, write, edit, grep) |
| Tokens used | From agent's usage report |
| Files touched | `git diff --stat` from initial state |
| Tests after | `cargo test` output: pass/fail counts |
| Warnings after | `cargo check 2>&1 \| grep warning` count |
| Commit quality | `git log -1 --format="%s%n%b"` |
| Correctness | Does DeduplicateFilter work correctly? Does test assertion match actual behavior? |

## Scoring Rubric (100 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| Correctness | 30 | All tests pass, DeduplicateFilter works, assertion is correct |
| Completeness | 20 | All 7 subtasks completed |
| Code quality | 15 | Doc comments, no warnings, idiomatic Rust |
| Efficiency | 15 | Fewer tool calls and tokens = better |
| Commit quality | 10 | Descriptive message, clean diff |
| Autonomy | 10 | No human intervention needed |

## Expected Result

- 16 tests pass (14 current + 2 new for DeduplicateFilter)
- 0 warnings
- All public types documented
- 1 commit with descriptive message
