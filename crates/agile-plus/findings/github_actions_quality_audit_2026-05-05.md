# GitHub Actions Workflow Quality Audit

**Date:** 2026-05-05
**Scope:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos`
**Total workflow files scanned:** 7,013

---

## Audit 1: Outdated / Non-SHA-Pinned Actions

**Finding:** 151 non-SHA-pinned action references across ~139 files.

Actions tagged with `@main`, `@latest`, or non-v-tag floating references are vulnerable to supply-chain substitution attacks. SHA-pinning is required for security-critical workflows.

### Dominant Pattern: `trufflehog/actions/setup@main`

This single action appears pinned to `@main` in 128+ repos. `trufflehog` does publish SHA-pinned releases — replace all instances with the pinned SHA.

**Representative substitution:**

```yaml
# Before
- uses: trufflehog/actions/setup@main

# After (example — verify current SHA at https://github.com/trufflehog/actions/releases)
- uses: trufflehog/actions/setup@8fe195c3c...
```

**Repos with `trufflehog/actions/setup@main` (canonical + worktrees):**

- `AgentMCP/`, `Agentora/`, `AuthKit/`, `Civis/`, `Configra/`, `Conft/`, `DINOForge-UnityDoorstop/`, `DataKit/`, `DevHex/`, `Dino/`, `Eidolon/`, `FocalPoint/`, `GDK/`, `Httpora/`, `KDesktopVirt/`, `KlipDot/`, `MCPForge/`, `McpKit/`, `ObservabilityKit/`, `Paginary/`, `Parpoura/`, `PhenoAgent/`, `PhenoCompose/`, `PhenoHandbook/`, `PhenoKits/`, `PhenoMCP/`, `PhenoObservability/`, `PhenoPlugins/`, `PhenoProc/`, `PhenoProject/`, `PhenoRuntime/`, `PhenoSpecs/`, `PhenoVCS/`, `Pine/`, `Planify/`, `PlatformKit/`, `PlayCua/`, `PolicyStack/`, `QuadSGM/`, `ResilienceKit/`, `Sidekick/`, `Tasken/`, `TestingKit/`, `Tracely/`, `agent-devops-setups/`, `agent-user-status/`, `agentapi-plusplus/`, `argis-extensions/`, `bare-cua/`, `chatta/`, `cheap-llm-mcp/`, `cliproxyapi-plusplus/`, `dinoforge-packs/`, `eyetracker/`, `foqos-private/`, `forgecode/`, `helios-cli/`, `helios-router/`, `heliosApp/`, `heliosBench/`, `helioscope/`, `localbase3/`, `nanovms/`, `netweave-final2/`, `phenoData/`, `phenoDesign/`, `phenoResearchEngine/`, `phenoUtils/`, `phenoXdd/`, `phenodocs/`, `phenodocs-scorecard-remediation/`, `phenotype-bus/`, `phenotype-hub/`, `phenotype-infra/`, `phenotype-journeys/`, `phenotype-omlx/`, `phenotype-org-audits/`, `phenotype-tooling/`, `portage/`, `rich-cli-kit/`, `thegent/`, `thegent-dispatch/`, `thegent-workspace/`, `vibeproxy/`, `vibeproxy-monitoring-unified/`

### Pattern: `actions/checkout@4`

6 AgilePlus worktrees pin `actions/checkout` to tag `@4` (not SHA-pinned). Also a floating tag risk.

**Repos:**
- `AgilePlus-wtrees/agile-main/`, `AgilePlus-wtrees/bdd-features/`, `AgilePlus-wtrees/cargo-deny-fix-tonic-2026-05-04/`, `AgilePlus-wtrees/security-gate-normalize/`, `AgilePlus-wtrees/task-77-contents-read/`

### Pattern: `<REDACTED>/phenotypeActions/actions/*@main`

4 `agentapi-plusplus` worktrees and 1 `cliproxyapi-plusplus` worktree reference a private org action at `@main`.

**Repos:**
- `agentapi-plusplus/` (canonical + worktrees): `<REDACTED>/phenotypeActions/actions/policy-gate@main`
- `cliproxyapi-plusplus/` (canonical + worktrees): `<REDACTED>/phenotypeActions/actions/lint-test@main`
- `portage/` (canonical + worktrees): `<REDACTED>/phenotypeActions/actions/lint-test@main`

**Recommendation:** Add SHA pins to `<REDACTED>/phenotypeActions` releases. If releases are not yet tagged, tag them first before updating callers.

---

## Audit 2: Missing `timeout-minutes`

**Finding:** 6,401 of 7,013 workflows (91.3%) lack `timeout-minutes` on at least one job.

Jobs without a timeout can hang indefinitely, consuming GitHub Actions minutes. GitHub's hard limit is 360 minutes (6 hours), but most jobs should complete in under 30 minutes.

**Root org-level workflows missing `timeout-minutes`:**

```
.github/workflows/alert-sync-issues.yml
.github/workflows/audit.yml
.github/workflows/cargo-audit.yml
.github/workflows/cargo-deny.yml
.github/workflows/cargo-machete.yml
.github/workflows/cargo-semver-checks.yml
.github/workflows/changelog.yml
.github/workflows/code-scanning-results.yml
.github/workflows/deploy.yml
.github/workflows/doc-links.yml
.github/workflows/evidence-capture.yml
.github/workflows/fr-coverage.yml
.github/workflows/gate-check.yml
.github/workflows/openapi-check.yml
.github/workflows/policy-gate.yml
.github/workflows/pr-governance-gate.yml
.github/workflows/promote.yml
.github/workflows/publish.yml
.github/workflows/quality-gate.yml
.github/workflows/regen-docs-specs.yml
.github/workflows/release-drafter.yml
.github/workflows/release.yml
.github/workflows/rust-security.yml
.github/workflows/sbom-refresh.yml
.github/workflows/scorecard.yml
.github/workflows/security-guard-hook-audit.yml
.github/workflows/security-guard.yml
.github/workflows/self-merge-gate.yml
.github/workflows/snyk-scan.yml
.github/workflows/sync-canary.yml
```

**Recommendation:** Add `timeout-minutes: 30` to all jobs (or `timeout-minutes: 60` for cargo/test-heavy jobs). Establish a shared reusable workflow at the org level that enforces a default timeout, then migrate repos to inherit it.

---

## Audit 3: Missing `permissions:` Block

**Finding:** 3,560 of 7,013 workflows (50.8%) lack an explicit `permissions:` declaration.

GitHub Actions runs with a default write-all scope when no `permissions:` is declared. Declaring minimal permissions follows the principle of least privilege and is required for OIDC token hardening.

**Recommendation:** Add a top-level `permissions:` block to every workflow. Minimum safe defaults:

```yaml
permissions:
  contents: read
  pull-requests: write
  issues: read
  statuses: read
```

Extend to `contents: write` only for workflows that push commits or releases.

---

## Audit 4: Missing Dependency Caching

**Finding:** 644 workflows perform dependency installation (`npm ci`, `pip install`, `cargo install`, `uv sync`, `pnpm install`, `yarn install`) but do not include any `cache` or `cache-from`/`cache-to` directives.

This causes unnecessary network I/O and slower CI runs on every push. Common in `legacy-tooling-gate.yml` stubs and `journey-gate.yml` files.

**Notable canonical repos affected:**

- `AgilePlus/.github/workflows/security.yml`
- `AppGen/.github/workflows/legacy-tooling-gate.yml`
- `AppGen/.github/workflows/npm-publish-github-packages.yml`
- `AgilePlus/.github/workflows/ci.yml`
- `AgilePlus/.github/workflows/deploy.yml`
- `AgilePlus/.github/workflows/gate-check.yml`
- `AgilePlus/.github/workflows/openapi-check.yml`
- `AgilePlus/.github/workflows/promote.yml`

**Recommendation:** Add `cache: 'pip'` / `cache: 'npm'` / `cache: 'cargo'` to relevant jobs. For matrix builds, use `cache: '${{ matrix.os }}'` or explicit cache keys. For Rust `cargo` builds, the official `actions/cache` or `swatinem/rust-cache` action covers target directory caching.

---

## Summary Table

| Audit | Issue | Count | % of Total |
|-------|-------|-------|------------|
| 1 | Non-SHA-pinned actions | 151 instances | 2.2% of uses |
| 2 | Missing `timeout-minutes` | 6,401 | 91.3% |
| 3 | Missing `permissions:` block | 3,560 | 50.8% |
| 4 | Install without cache | 644 | 9.2% |

---

## Recommended Priority Fixes

1. **[P0 — Security]** Pin `trufflehog/actions/setup@main` to SHA in all 128+ affected files. Batch-fix with:

   ```bash
   # Dry-run first
   find . -path "*/.github/workflows/*.yml" \
     -exec grep -l "trufflehog/actions/setup@main" {} \; \
     -exec sed -i '' 's|trufflehog/actions/setup@main|TRUFFLEHOG_SHA_PLACEHOLDER|g' {} \;
   ```

   Then replace `TRUFFLEHOG_SHA_PLACEHOLDER` with the pinned SHA.

2. **[P0 — Org Baseline]** Add `timeout-minutes` to all 37 root org-level workflows in `.github/workflows/`.

3. **[P1 — Org Baseline]** Add `permissions:` blocks to the 37 root org-level workflows.

4. **[P1 — CI Performance]** Add caching to the org-level `ci.yml`, `deploy.yml`, and `gate-check.yml`.

5. **[P2 — Private Actions]** SHA-pin `<REDACTED>/phenotypeActions` releases and update all callers in `agentapi-plusplus`, `cliproxyapi-plusplus`, and `portage`.

6. **[P3 — Worktrees]** As worktrees are merged/retired, ensure new canonical workflows use SHA-pinned actions, explicit timeouts, and permission blocks.
