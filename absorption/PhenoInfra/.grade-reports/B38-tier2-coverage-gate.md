# B38 — Tier-2 Coverage Gate Audit

**Date:** 2026-06-24
**Target:** `C:\Users\koosh\phenotype-infra-ci-fix`
**Standard:** Tier-2 = coverage >= 71%

---

## 1. Tier-2 Requirement

| Requirement          | Status |
|----------------------|--------|
| Coverage workflow exists | ✅ (2 files exist) |
| Actual coverage tool runs | ❌ **Both are stubs** |
| Threshold >= 71% configured | ❌ **Not configured** |
| Gate blocks PR if below threshold | ❌ **Not configured** |

---

## 2. Workflow Analysis

### 2.1 `coverage.yml`
- **Triggers:** `push: [main]`, `pull_request: [main]`
- **Structure:** Has three jobs — `lint`, `test`, `coverage` — but **all are stubs:**
  ```yaml
  - name: Run lint
    run: echo "Running language-specific lint"
  - name: Run tests
    run: echo "Running language-specific tests"
  - name: Generate coverage
    run: echo "Generating coverage (language-specific)"
  ```
- **Threshold:** ❌ Not configured (no coverage tool, no threshold check, no upload)
- **Permissions:** `id-token: write` (OIDC trust) but no actual coverage tooling wired up

### 2.2 `fr-coverage.yml`
- **Triggers:** `on: [pull_request]`
- **Structure:** Single job with a single step stub:
  ```yaml
  - run: echo "FR coverage check (phenotype-tooling integration)"
  ```
- **Threshold:** ❌ Not configured

---

## 3. Gap Analysis

| Gap | Severity | Details |
|-----|----------|---------|
| No actual coverage tool runs | **Critical** | Both workflows execute placeholder `echo` commands, not actual coverage instrumentation |
| No threshold enforcement | **Critical** | No mechanism to compare coverage % against a 71% threshold |
| No PR status check for coverage | **High** | No coverage report is produced or uploaded; PRs cannot be gated on coverage |
| Missing cargo tooling | **High** | `cargo tarpaulin`, `grcov`, or `cargo-llvm-cov` not wired up |
| Missing codecov/codacy upload | **Medium** | No upload to coverage visualization services |

---

## 4. Suggested Implementation (for workflow maintainers)

### 4.1 Recommended coverage workflow

```yaml
# Replace contents of coverage.yml or create a dedicated Rust coverage workflow:
#
# on:
#   pull_request:
#     branches: [main]
#
# jobs:
#   coverage:
#     runs-on: ubuntu-latest
#     steps:
#       - uses: actions/checkout@v4
#       - uses: dtolnay/rust-toolchain@stable
#         with:
#           components: llvm-tools-preview
#       - uses: Swatinem/rust-cache@v2
#
#       - name: Install cargo-llvm-cov
#         uses: taiki-e/install-action@cargo-llvm-cov
#
#       - name: Generate coverage data
#         run: cargo llvm-cov --workspace --lcov --output-path lcov.info
#         working-directory: iac
#
#       - name: Check coverage threshold (>= 71%)
#         run: |
#           COVERAGE=$(cargo llvm-cov --workspace --json | jq -r '.data[0].totals.lines.percent')
#           if (( $(echo "$COVERAGE < 71" | bc -l) )); then
#             echo "::error::Coverage ${COVERAGE}% is below 71% threshold"
#             exit 1
#           fi
#           echo "Coverage: ${COVERAGE}% — passes threshold"
#
#       - name: Upload to codecov.io
#         uses: codecov/codecov-action@v4
#         with:
#           files: lcov.info
#           fail_ci_if_error: false
```

### 4.2 Alternative: Use `cargo-tarpaulin`

```yaml
#       - uses: actions-rs/tarpaulin@v0.1
#         with:
#           version: '0.22.0'
#           args: '--workspace --out Lcov --output-dir ./coverage'
#
#       - name: Check threshold
#         run: |
#           COV=$(grep -oP '^\d+\.\d+%' coverage.lcov | head -1 | sed 's/%//')
#           if (( $(echo "$COV < 71" | bc -l) )); then
#             echo "::error file=coverage.report::Coverage ${COV}% < 71%"
#             exit 1
#           fi
```

---

## 5. Additional Observations

- The `coverage.yml` workflow already has a clean structure (lint → test → coverage jobs) and proper PR trigger. It only needs **actual tool integration** and **threshold configuration**.
- The `fr-coverage.yml` appears to be a future placeholder for functional-requirement coverage (not code coverage).
- The `ci.yml` runs `cargo test` but collects no coverage data.
- The `release.yml` runs tests but also collects no coverage data.

---

## 6. Verdict

**Tier-2 coverage gate (>= 71%) is FAILING (🔴).**

Both coverage-related workflow files exist but are **non-functional stubs** — they only print echo messages. There is:
- No actual coverage instrumentation tool wired up
- No threshold configuration or enforcement
- No coverage report upload or PR status check

**Action required:** At minimum, add a real coverage tool (e.g., `cargo-llvm-cov`, `cargo-tarpaulin`, `grcov`), configure the 71% threshold, and ensure the step fails the workflow if coverage is below threshold.
