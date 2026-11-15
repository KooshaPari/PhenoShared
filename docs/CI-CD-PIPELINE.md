# CI/CD Pipeline Documentation

## Overview

AgilePlus implements a comprehensive four-phase CI/CD pipeline using GitHub Actions:

1. **CI (ci.yml)** — Build, Lint, Test, Coverage
2. **Security (security.yml)** — Audit, Secrets, Licenses, SAST
3. **Benchmarks (benchmark.yml)** — Performance Regression Detection
4. **Release (release.yml)** — Automated Publishing

All workflows are triggered on push to `main`, pull requests, and other specific conditions. This document describes each workflow in detail.

## Quick Links

- **CI Workflow**: https://github.com/KooshaPari/phenotype-infrakit/actions/workflows/ci.yml
- **Security Workflow**: https://github.com/KooshaPari/phenotype-infrakit/actions/workflows/security.yml
- **Benchmark Workflow**: https://github.com/KooshaPari/phenotype-infrakit/actions/workflows/benchmark.yml
- **Release Workflow**: https://github.com/KooshaPari/phenotype-infrakit/actions/workflows/release.yml
- **Coverage Dashboard**: https://codecov.io/gh/&lt;REDACTED&gt;/phenotype-infrakit

## Workflow 1: CI (Build, Lint, Test, Coverage)

**File**: `.github/workflows/ci.yml`

**Purpose**: Automatically build, lint, test, and measure code coverage on every push and pull request.

**Triggers**:

- Push to `main` branch
- Pull requests to `main` branch
- Manual trigger (`workflow_dispatch`)

### Jobs

#### 1.1 Build Job

- **Runs on**: ubuntu-latest, macos-latest (parallel)
- **Components**: Rust toolchain (stable) + clippy + rustfmt
- **Steps**:
  1. Checkout code
  2. Install Rust with components
  3. Cache dependencies (Swatinem/rust-cache)
  4. Run `cargo build --release --all --verbose`
- **Duration**: ~2-5 min (with cache)
- **Artifacts**: Release binaries

#### 1.2 Lint Job

- **Runs on**: ubuntu-latest
- **Steps**:
  1. Install Rust with clippy and rustfmt
  2. Run `cargo clippy --all --all-targets -- -D warnings`
  3. Check `cargo fmt --all -- --check`
- **Duration**: ~2-3 min
- **Fails if**: Any clippy warning OR formatting issues

#### 1.3 Test Job

- **Runs on**: ubuntu-latest
- **Steps**:
  1. Run `cargo test --release --all --verbose`
- **Duration**: ~5-10 min
- **Output**: Test results summary

#### 1.4 Python Tests Job

- **Runs on**: ubuntu-latest
- **Steps**:
  1. Set up Python 3.11
  2. Install pytest, ruff
  3. Run `ruff check src/ tests/`
  4. Run `pytest tests/ -v`
- **Duration**: ~1-2 min
- **Output**: Python test results

#### 1.5 Coverage Job

- **Runs on**: ubuntu-latest
- **Steps**:
  1. Install tarpaulin
  2. Generate HTML coverage: `cargo tarpaulin --out Html`
  3. Upload to Codecov.io (optional, non-blocking)
  4. Upload artifact
- **Duration**: ~10-15 min
- **Output**: Coverage report (HTML + Codecov)
- **Target**: >=80% coverage (advisory)

### Environment Variables

```yaml
env:
  CARGO_TERM_COLOR: always
  RUSTFLAGS: -D warnings
```

---

## Workflow 2: Security (Audit, Secrets, Licenses, SAST)

**File**: `.github/workflows/security.yml`

**Purpose**: Detect vulnerabilities, secrets, licensing issues, and run static analysis.

**Triggers**:

- Push to `main` branch
- Pull requests to `main` branch
- Daily schedule (2am UTC)
- Manual trigger (`workflow_dispatch`)

### Jobs

#### 2.1 Cargo Audit Job

- **Tool**: `cargo audit`
- **Purpose**: Check for known vulnerabilities in Rust dependencies
- **Command**: `cargo audit --all-features --deny warnings`
- **Duration**: ~1-2 min
- **Fails if**: Critical or high severity vulnerabilities found

#### 2.2 Cargo Deny Job

- **Tool**: `cargo-deny`
- **Purpose**: Enforce dependency, license, and source policies
- **Configuration**: Uses existing `deny.toml` file
- **Checks**:
  1. Advisories (known vulnerabilities with suppressions)
  2. Licenses (MIT, Apache-2.0, BSD, ISC, etc.)
  3. Sources (no unknown git sources)
- **Duration**: ~2-3 min
- **Fails if**: Policy violation detected

#### 2.3 Gitleaks Job

- **Tool**: Gitleaks GitHub Action
- **Purpose**: Detect secrets and sensitive information in git history
- **Features**:
  - Scans entire repository with `fetch-depth: 0`
  - Detects API keys, passwords, tokens
  - Verbose output for debugging
- **Duration**: ~1-2 min
- **Fails if**: Secrets detected

#### 2.4 CodeQL Analysis Job

- **Tool**: GitHub CodeQL (built-in SAST)
- **Languages**: C++ (from Rust compilation), Python
- **Purpose**: Static Application Security Testing
- **Output**: Code scanning alerts in GitHub Security tab
- **Permissions**: Requires `security-events: write`
- **Duration**: ~5-10 min per language

#### 2.5 Python Security Job

- **Tools**: Bandit (SAST), Safety (dependencies)
- **Purpose**: Security checks for Python code
- **Steps**:
  1. Run `bandit -r src/ tests/` (non-blocking)
  2. Run `safety check --json` (non-blocking)
- **Duration**: ~1-2 min
- **Note**: Non-blocking to allow for false positives review

---

## Workflow 3: Benchmarks (Performance Regression Detection)

**File**: `.github/workflows/benchmark.yml`

**Purpose**: Detect performance regressions and track performance trends.

**Triggers**:

- Push to `main` branch
- Pull requests to `main` branch
- Manual trigger (`workflow_dispatch`)

### Jobs

#### 3.1 Benchmark Job

- **Runs on**: ubuntu-latest
- **Steps**:
  1. Check for `benches/` directory
  2. Compile benchmarks: `cargo bench --all --no-run`
  3. Run benchmarks: `cargo bench --all -- --verbose --output-format bencher`
  4. Store results using benchmark-action/github-action-benchmark
  5. Upload artifact for archive
- **Duration**: ~15-20 min
- **Regression Threshold**: >5% drop triggers warning
- **Output**: Benchmark results artifact + PR comment
- **Non-blocking**: `continue-on-error: true` if no benchmarks

### Baseline Storage

- Baseline stored in `benchmark-baselines` git branch
- Results tracked over time for trend analysis
- Auto-push disabled to prevent conflicts

---

## Workflow 4: Release (Build and Publish)

**File**: `.github/workflows/release.yml`

**Purpose**: Automatically build and publish releases when tags are pushed.

**Triggers**:

- Push tag matching `v*.*.*` (e.g., `v1.0.0`, `v2.1.3-rc1`)
- Manual trigger with version input

### Jobs

#### 4.1 Build Release Job

- **Runs on**: Multiple platforms (parallel)
  - `x86_64-unknown-linux-gnu` (Ubuntu)
  - `x86_64-apple-darwin` (macOS Intel)
  - `aarch64-apple-darwin` (macOS ARM64)
- **Steps**:
  1. Checkout tag
  2. Install Rust for target platform
  3. Build: `cargo build --release --all --target`
  4. Strip debug symbols: `strip binary`
  5. Upload artifact
- **Duration**: ~10-15 min per platform
- **Output**: Platform-specific binaries

#### 4.2 Create Release Job

- **Runs on**: ubuntu-latest
- **Depends on**: build-release (waits for all binaries)
- **Permissions**: Requires `contents: write`
- **Steps**:
  1. Download all platform artifacts
  2. Determine version from tag or input
  3. Generate release notes
  4. Create GitHub Release with ncipollo/release-action
  5. Attach all platform binaries
- **Duration**: ~2-3 min
- **Output**: GitHub Release page with binaries

### Release Process

```bash
# 1. Tag commit
git tag -a v1.0.0 -m "Release notes here"

# 2. Push tag
git push origin v1.0.0

# 3. GitHub automatically:
#    - Detects tag
#    - Triggers release workflow
#    - Builds binaries for all platforms
#    - Creates release page
#    - Attaches binaries
```

### Download Binaries

```bash
gh release view v1.0.0
gh release download v1.0.0 --pattern "agileplus-*"
```

---

## Performance Characteristics

### Build Times (with Swatinem cache)

| Platform       | First Run | Cached Run |
| -------------- | --------- | ---------- |
| Linux (x86_64) | ~8 min    | ~2 min     |
| macOS (x86_64) | ~10 min   | ~3 min     |
| macOS (ARM64)  | ~8 min    | ~2-3 min   |

### Workflow Duration

| Workflow   | Parallel        | Total Time | Cost          |
| ---------- | --------------- | ---------- | ------------- |
| CI         | 3 parallel jobs | ~15 min    | Free (ubuntu) |
| Security   | Sequential      | ~10 min    | Free (ubuntu) |
| Benchmarks | 1 job           | ~20 min    | Free (ubuntu) |
| Release    | Parallel builds | ~30 min    | Free (ubuntu) |

### Monthly Cost Estimate

**GitHub Actions Free Tier**: 20,000 minutes/month

**Current setup** (ubuntu-only, no macOS/Windows runners):

| Scenario            | Monthly Usage              |
| ------------------- | -------------------------- |
| 10 commits/day      | ~100 hours (CI + Security) |
| 2 releases/month    | ~2 hours (Release)         |
| Benchmarks on PR    | ~10 hours                  |
| Daily security scan | ~4 hours                   |
| **Total**           | **~116 hours**             |

**Status**: Well within free tier (20,000 min = 333 hours)

---

## Configuration Reference

### deny.toml (Security Policies)

Located in repository root. Controls:

```toml
[licenses]
allow = ["MIT", "Apache-2.0", ...]  # Allowed licenses

[advisories]
ignore = [
    { id = "RUSTSEC-2025-XXXX", reason = "..." },
]

[sources]
unknown-git = "deny"  # Reject unknown git sources
```

### Workspace Configuration (Cargo.toml)

```toml
[workspace]
resolver = "2"
members = ["crates/*"]

[profile.release]
opt-level = "z"
lto = true
codegen-units = 1
strip = true
```

---

## Status Checks

Required status checks for branch protection:

- ✅ `build (ubuntu-latest)`
- ✅ `build (macos-latest)`
- ✅ `lint`
- ✅ `test`
- ✅ `python-tests`
- ✅ `cargo-audit`
- ✅ `cargo-deny`

Optional checks:

- `CodeQL C++` (code scanning)
- `CodeQL Python` (code scanning)
- `Gitleaks` (secret detection)
- `Benchmark` (performance trend)

---

## Troubleshooting

### Workflow Not Triggering

1. Verify workflow is enabled:

   ```bash
   gh workflow list
   ```

2. Check branch filter:

   ```bash
   grep -A 2 "on:" .github/workflows/ci.yml
   ```

3. Ensure commit is on `main`:
   ```bash
   git branch -a --contains HEAD
   ```

### Build Timeout

- Increase timeout: `timeout-minutes: 30`
- Optimize slow dependencies
- Check for large binary files

### Coverage Not Uploading

- Verify CODECOV_TOKEN secret exists
- Check Codecov account permissions
- Review upload logs in Actions

### Benchmark Baseline Issue

- Reset baseline on `benchmark-baselines` branch
- Delete old results: `git push -d origin refs/heads/benchmark-baselines`

---

## Best Practices

1. **Test Locally First**:

   ```bash
   cargo build --release
   cargo clippy --all -- -D warnings
   cargo test --all
   ```

2. **Keep Dependencies Updated**:

   ```bash
   cargo audit        # Check vulnerabilities
   cargo update       # Update dependencies
   cargo deny check   # Verify policies
   ```

3. **Monitor Coverage Trends**:
   - Review Codecov dashboard monthly
   - Set coverage goals per crate
   - Fix coverage gaps before release

4. **Review Security Alerts**:
   - Check GitHub Security tab weekly
   - Address high/critical issues immediately
   - Document suppressions in `deny.toml`

5. **Test Releases Locally**:
   ```bash
   cargo build --release --target x86_64-unknown-linux-gnu
   ./target/x86_64-unknown-linux-gnu/release/agileplus --version
   ```

---

## Integration with Local Development

### Pre-commit Hook (Recommended)

```bash
#!/bin/bash
cargo clippy --all -- -D warnings || exit 1
cargo fmt --all -- --check || exit 1
cargo test --all || exit 1
```

Save as `.git/hooks/pre-commit` and run `chmod +x .git/hooks/pre-commit`.

### IDE Configuration

**VS Code** (`settings.json`):

```json
{
  "rust-analyzer.checkOnSave.command": "clippy",
  "rust-analyzer.checkOnSave.extraArgs": ["--", "-D", "warnings"],
  "[rust]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "rust-lang.rust-analyzer"
  }
}
```

**IntelliJ IDEA**:

- Settings > Languages & Frameworks > Rust > Clippy
- Enable "External linter" with `--all-targets -- -D warnings`

---

## Future Enhancements

- [ ] Performance regression alerts (Slack/Discord)
- [ ] Automated dependency updates (Dependabot)
- [ ] MSRV validation (Minimum Supported Rust Version)
- [ ] Artifact signing and attestation
- [ ] Contract testing for crate consumers
- [ ] SLSA provenance generation
- [ ] Nightly builds on schedule
- [ ] Code coverage trend reports

---

## See Also

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Codecov Integration](https://docs.codecov.io/)
- [Cargo Book](https://doc.rust-lang.org/cargo/)
- [Rust Security Guidelines](https://anssi-fr.github.io/rust-guide/)
- [CI-CD Setup Instructions](CI-CD-SETUP.md)

## Python Ruff ratchet and measured debt

The ratchet rule is: new and modified Python must be clean; pre-existing debt is
measured and only shrinks. On pull requests, added and modified `*.py` files are
checked with blocking Ruff lint and format steps. Whole-tree lint and format
remain visible advisory steps with `continue-on-error: true`. A failed shallow
base-commit fetch prints a notice and skips the changed-file check because an
infrastructure flake must not red the gate. Push events run the advisory checks.
The `ci / lint` aggregator still classifies the Python job as ADVISORY, so
"blocking" currently means failing the Python job, not blocking the merge.

The baseline below was measured on **2026-11-15** against `origin/main`
`e6969738b`, macOS arm64, with the CI-pinned Ruff **0.16.5** installed through
`uv tool run` over a pristine `git archive` of that commit. It is **18,018
diagnostics over 2,710 files across 197 distinct rules**. An earlier
measurement recorded in the workflow comment on 2026-11-13 read 18,049 on the
Linux runner and 18,051 on macOS arm64 (2 fewer on Linux); the difference from
18,018 is drift in the tree between the two commits, not a change of tool
version. Both numbers are quoted because replacing one with the other without
saying which commit it came from is how a stale figure ends up looking current.

One consequence worth stating: a changed-file ratchet is strict. Editing a
legacy file makes that whole file blocking, so a PR that touches a file with
pre-existing violations must clean that file, or leave it alone. That is
deliberate - it is what makes the debt monotone - but it means the first
contributor to touch a noisy file inherits its lint debt and should expect to
spend a bounded cleanup pass there.

The top ten rules are:

| Rule   | Diagnostics |
| ------ | ----------: |
| UP006  |       3,019 |
| UP045  |       2,435 |
| I001   |       1,714 |
| S101   |       1,492 |
| F401   |       1,178 |
| W293   |       1,022 |
| UP035  |         888 |
| BLE001 |         731 |
| E501   |         371 |
| TRY401 |         333 |

The measured top-level breakdown is:

| Tree           | Diagnostics | Files |
| -------------- | ----------: | ----: |
| docs           |       4,871 |   977 |
| agents         |       4,675 |   635 |
| crates         |       3,772 |   259 |
| absorption     |       1,973 |   287 |
| python         |         833 |   152 |
| scripts        |         328 |    85 |
| researchledger |         290 |    89 |
| researchintel  |         295 |    12 |
| agileplus      |         245 |    24 |
| audits         |         188 |    39 |

Whole-tree safe autofix was rejected: it changed **4,437 files**, with
**+118,562 / -63,065 lines**, and still left **6,233 errors**. This is not an
acceptable small CI change. The advisory baseline is visible debt, not permission
for it to grow by accident. This ratchet checks touched files, not a numerical
whole-tree debt ceiling, so reviewers must ensure cleanup only shrinks the debt.

There is pin drift: `.github/workflows/ci.yml` installs **ruff==0.16.5**, while
`.trunk/trunk.yaml` pins **0.17.4**. CI enforces **0.16.5**. This change does not
silently upgrade either tool pin.

Stage 2 has three steps:

1. Clean one first-party tree and verify both lint and format at the CI pin.
2. Add that clean tree to the blocking path list so unchanged files in the tree
   are checked too, in addition to the current changed-file ratchet.
3. Promote the Python job to HARD in the aggregator only after the checked paths
   are clean and the lane is green. The ratchet makes the lane green without
   hiding the whole-tree debt, but promotion still requires clean checked paths.

### Known parse defects left deliberately unresolved

A lint/parse finding whose correct behaviour is unknown is recorded, not silenced.

- `crates/argis-extensions/scripts/adr_backlink_check.py`: not Python source at all, the `.py` blob holds three lines of captured `git` error output. No live executor was found by basename outside root docs. Fix deferred because the genuine validator's proven provenance is UNKNOWN, and renaming could break unknown external callers.
- `crates/policystack/scripts/policy/c100_forensic_bundle_gap_gate.py:92`: genuine missing-suite syntax error, `if not _truthy(...)` has no body before the following top-level `for`. Intent UNKNOWN, so adding `pass` would silence a real defect. The fix needs the gap-counting contract.
- `docs/absorbed-from-PhenoTooling/scripts/stream_compat_matrix.py:304`: invalid conditional used as a dict-unpack operand. Inside an archival corpus that `ABSORPTION.md` says is not built and not linted, so it is out of scope for the ratchet by design.
- `phenotype-hub/SECURITY.md`: dangling symlink to `../template-commons/SECURITY.md`, which does not exist in the merged tree. Root `SECURITY.md` exists. Retargeting needs a decision about which disclosure policy is authoritative, and guessing on a security policy is worse than leaving it visible.
