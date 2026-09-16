# B32 — Tier-1 PR Enforcement Audit

**Date:** 2026-06-24
**Target:** `C:\Users\koosh\phenotype-infra-ci-fix`
**Standard:** Tier-1 = security scan (cargo deny/audit/trufflehog), SBOM, LICENSE check, CHANGELOG update

---

## 1. Tier-1 Requirements

| Requirement               | Status |
|---------------------------|--------|
| Cargo deny                | ✅     |
| Cargo audit               | ✅     |
| Trufflehog secrets scan   | ✅     |
| CodeQL / SAST             | ✅     |
| Trivy filesystem scan     | ✅     |
| **SBOM generation**       | ❌ **Missing** |
| **LICENSE file check**    | ❌ **Missing** |
| **CHANGELOG update check**| ❌ **Missing** |

---

## 2. Relevant Workflow Analysis

### 2.1 `cargo-deny.yml`
- **PR trigger:** `pull_request: { branches: [main] }` ✅
- **Command:** `cargo deny check advisories` on `iac/Cargo.toml`
- **Additional:** `workflow_dispatch` for manual runs
- **Covers:** Advisory scanning (RustSec DB), license compliance (via deny.toml), duplicate crate detection, etc.
- **Verdict:** ✅ Adequate.

### 2.2 `ci.yml` — `audit` job
- **PR trigger:** Inherited from `ci.yml` (`pull_request: { branches: [main] }`) ✅
- **Jobs:** `cargo-deny` action (full deny), `cargo audit` (vulnerability scan via `rustsec/audit-check`)
- **Verdict:** ✅ Covers both deny and audit on PR.

### 2.3 `trufflehog.yml`
- **PR trigger:** `pull_request:` (any branch) ✅
- **Configuration:** `fetch-depth: 0`, scans against base branch, `--only-verified` flag
- **Verdict:** ✅ Covers secrets leak detection on every PR.

### 2.4 `audit.yml`
- **PR trigger:** `pull_request:` (any branch) ✅
- **Also:** Push to main/master, daily scheduled run
- **Tool:** `aquasecurity/trivy-action` (filesystem scan, CRITICAL/HIGH severity)
- **Verdict:** ✅ Covers container/filesystem vulnerability scanning on PR.

### 2.5 `codeql.yml`
- **PR trigger:** `pull_request: { branches: [main] }` ✅
- **Analysis:** Rust language via `github/codeql-action`
- **Verdict:** ✅ SAST coverage on PR.

---

## 3. Gap Analysis

### 3.1 ❌ SBOM Generation (`cyclonedx` / `spdx`)
- **Finding:** No workflow generates a Software Bill of Materials (SBOM) on PR or release.
- **Why it matters:** SBOMs are required for supply-chain transparency and are increasingly a compliance requirement (EO 14028, NTIA minimum elements).
- **Suggested fix:**

  ```yaml
  # Consider adding an SBOM step to ci.yml's audit job, or a new workflow:
  # .github/workflows/sbom.yml
  # on: [pull_request, push]
  # jobs:
  #   sbom:
  #     runs-on: ubuntu-latest
  #     steps:
  #       - uses: actions/checkout@v4
  #       - name: Generate SBOM (Cargo)
  #         uses: cdactyl/sbom-generator-action@v1
  #         # Or use cyclonedx-bom for Rust:
  #         # cargo install cargo-cyclonedx && cargo cyclonedx
  ```

### 3.2 ❌ LICENSE File Check
- **Finding:** No workflow verifies that LICENSE headers exist in source files or that a top-level LICENSE file is present and valid.
- **Why it matters:** License compliance ensures the project can be consumed internally and externally without legal risk.
- **Suggested fix:**

  ```yaml
  # In quality-gate.yml or a new workflow, add:
  # - name: Check top-level LICENSE exists
  #   run: test -f LICENSE || { echo "::error::LICENSE file missing"; exit 1; }
  #
  # - name: REUSE compliance (optional)
  #   uses: fsfe/reuse-action@v3
  ```

### 3.3 ❌ CHANGELOG Update Check
- **Finding:** No workflow validates that `CHANGELOG.md` is updated in a PR.
- **Why it matters:** CHANGELOG hygiene ensures release notes are always accurate and audit trail is maintained.
- **Suggested fix:**

  ```yaml
  # In quality-gate.yml or a new workflow, add:
  # - name: Check CHANGELOG update
  #   uses: dangoslen/changelog-enforcer@v3
  #   with:
  #     changeLogPath: CHANGELOG.md
  #     skipLabels: skip-changelog
  ```

---

## 4. Summary Matrix

| Security/Compliance Control | Workload(s)         | PR-Enforced | Notes |
|----------------------------|---------------------|-------------|-------|
| Cargo deny (advisories)    | `cargo-deny.yml`, `ci.yml` | ✅ | Comprehensive |
| Cargo audit                | `ci.yml`            | ✅ | RustSec vuln DB |
| Trufflehog (secrets)       | `trufflehog.yml`    | ✅ | `--only-verified` |
| Trivy (filesystem vulns)   | `audit.yml`         | ✅ | CRITICAL+HIGH |
| CodeQL (SAST)              | `codeql.yml`        | ✅ | Rust analysis |
| **SBOM generation**        | **None**            | ❌ | **Not implemented** |
| **LICENSE compliance**     | **None**            | ❌ | **Not implemented** |
| **CHANGELOG enforcement**  | **None**            | ❌ | **Not implemented** |

---

## 5. Verdict

**Tier-1 PR enforcement is PARTIALLY PASSING (🟡).**

Security scanning is well covered: cargo deny (advisories + licenses), cargo audit (vulnerabilities), trufflehog (secrets), trivy (filesystem), and CodeQL (SAST) are all enforced on PR.

**Three gaps exist that prevent full compliance:**
1. **SBOM generation** — no workflow produces a CycloneDX or SPDX SBOM
2. **LICENSE check** — no workflow verifies LICENSE file presence or REUSE compliance
3. **CHANGELOG update** — no workflow enforces CHANGELOG.md modification on PR

These are moderate-severity gaps. Security scans are complete, but supply-chain transparency and documentation hygiene controls are missing.
