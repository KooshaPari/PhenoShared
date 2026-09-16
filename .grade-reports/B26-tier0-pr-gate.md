# B26 — Tier-0 PR Enforcement Audit

**Date:** 2026-06-24
**Target:** `C:\Users\koosh\phenotype-infra-ci-fix`
**Standard:** Tier-0 = build green, test-unit green, fmt/clippy/lint green, typecheck green

---

## 1. Tier-0 Requirements

| Requirement   | Rust Equivalent     | Status |
|---------------|---------------------|--------|
| Build green   | `cargo check`       | ✅     |
| Test green    | `cargo test`        | ✅     |
| Fmt/clippy    | `cargo fmt --check` + `cargo clippy` | ✅ |
| Lint          | `cargo clippy -D warnings` | ✅ |
| Typecheck     | `cargo check` (includes typechecking) | ✅ |

---

## 2. Relevant Workflow Analysis

### 2.1 `ci.yml`
- **PR trigger:** `pull_request: { branches: [main] }` ✅
- **Jobs:**
  - `check` — `cargo fmt --check`, `cargo check --workspace --all-targets --locked`, `cargo clippy --workspace --all-targets --locked -- -D warnings` ✅
  - `test` — `cargo test --workspace --locked --all-features` ✅
- **Coverage:** Full Tier-0 on every PR to `main`.

### 2.2 `iac-rust.yml`
- **PR trigger:** `pull_request:` with path restrictions (`iac/Cargo.toml`, `iac/oci-lottery/**`, etc.) ✅ (scoped)
- **Jobs:**
  - `workspace` — `cargo fmt --check`, `cargo check`, `cargo clippy -D warnings`, `cargo test` ✅
  - `landing-bootstrap` — same four steps in standalone crate ✅
- **Note:** Path-restricted — runs only when iac-specific files change.

### 2.3 `quality-gate.yml`
- **PR trigger:** `pull_request: { branches: [main] }` ✅
- **Jobs:**
  - `go-vet` — `go vet ./...` (Go typecheck/lint)
  - `cargo-check` — `cargo check --workspace`, `cargo fmt --check` (Rust subset)
  - `go-lint` — `golangci-lint`
  - `security` — `gosec` + `govulncheck` (Go security, not strictly Tier-0)
- **Note:** Quality gate is more focused on Go code and security; `cargo-check` provides partial Tier-0 for Rust (missing clippy and test).

---

## 3. Gap Analysis

| Gap | Severity | Details |
|-----|----------|---------|
| No explicit `cargo clippy` in `quality-gate.yml`'s `cargo-check` job | Low | `ci.yml` already covers clippy on PR; quality gate is supplementary |
| No dedicated "typecheck" job label | Informational | `cargo check` is the Rust typecheck — functionally equivalent |
| No typecheck for non-Rust (Terraform, Ansible) | Low | `terraform-plan.yml` has `terraform validate` on PR but no HCL typechecker; not required by Tier-0 |

---

## 4. Suggested Additions (for workflow maintainers)

### 4.1 Consider adding to `ci.yml` (if not already present)

```yaml
# In ci.yml 'check' job — already present. No changes needed.
```

### 4.2 If `iac-rust.yml` is the primary Rust gate, it already satisfies Tier-0.

### 4.3 Optional enhancement — add to `quality-gate.yml`:
```yaml
# Uncomment or add a clippy step to the cargo-check job:
# - name: cargo clippy
#   run: cargo clippy --workspace --locked -- -D warnings
# - name: cargo test
#   run: cargo test --workspace --locked
```

> **Current state:** The `quality-gate.yml` `cargo-check` job currently runs only `cargo check` and `cargo fmt --check`. Adding `cargo clippy` and `cargo test` would make it a full Tier-0 duplicate gate. This is optional since `ci.yml` already provides coverage.

---

## 5. Verdict

**Tier-0 PR enforcement is PASSING (🟢).**

All four Tier-0 requirements (build, test, fmt/clippy, typecheck) are enforced on every PR through `ci.yml` (comprehensive) and `iac-rust.yml` (path-scoped). The `quality-gate.yml` provides a supplementary gate with partial coverage. No blocking gaps found.
