# AgilePlus CI Gate Triage

Generated: 2026-06-25. Diagnosis based on workflow source + PR #805 (`gh pr checks` / `gh run view --log-failed`).

## Summary

| Gate | Blocks merge? | Root cause | Fix class | Workflow fix applied? |
|------|---------------|------------|-----------|----------------------|
| Autograder | Advisory* | Clones missing private repo `<REDACTED>/phenoShared` before any Rust work | **(a) broken** | Yes — removed stale phenoShared checkout |
| Conventional Commits | Advisory* | Commitlint `subject-case` rejects Title-Case subjects (e.g. `AgilePlus`) | **(b) comply** | No — authors must use lowercase subjects |
| gitleaks scan | Advisory* | Invalid action pin `gitleaks/gitleaks-action@1c4d3b6…` (placeholder SHA); config path `.gitleaks.toml` vs `gitleaks.toml` | **(a) broken** | Yes — pin `@v2`, fix config path |
| governance-index | Advisory* | `kitty-specs/INDEX.md` drifts from generator on every PR even when specs unchanged | **(a) broken** | Yes — PR path filter + skip verify when index unchanged |
| guard | Advisory* | pre-commit `legacy-tooling-scan` expects local scanner/policy files that are not vendored | **(a) broken** | Yes — bootstrap scanner + policy before pre-commit |
| policy-gate | **REQUIRED** | `fix/*` → `main` blocked unless `layered-pr-exception` label | **(b) comply** | No — intentional branch policy |
| pr-governance-gate | **REQUIRED** | Requires PR template sections, layered targeting, all checks green | **(b) comply** | No — meta-gate; passes when other gates + body comply |
| sonar | Advisory* | Empty `sonar-project.properties` — missing `sonar.projectKey` / `sonar.organization` | **(a) broken** | Yes — pass keys via workflow `args` |
| SonarCloud | Advisory* | Same as `sonar` + needs org `SONAR_TOKEN` secret for authenticated analysis | **(c) user-gated** | Partial — keys in workflow; token must be set in repo settings |
| spec-first | Advisory* | PR body must contain `spec: eco-NNN-slug` matching an active `kitty-specs/` entry | **(b) comply** | No — intentional traceability gate |
| Workspace Path Dependency Audit | Advisory* | Same broken `phenoShared` clone as Autograder | **(a) broken** | Yes — removed stale phenoShared checkout |

\*Not listed in `.github/RULESET_BASELINE.md` required checks (`policy-gate`, `pr-governance-gate`, `verify`, `semgrep`, `secrets`, `lint-rust`, `license-check`). Still surfaces as red on PRs and is aggregated by `pr-governance-gate`.

## Per-gate detail

### Autograder (`autograder.yml`)

- **Required vs advisory:** Advisory for ruleset baseline; fails on every PR today.
- **Why it fails:** Step `Checkout phenoShared sibling` clones `https://github.com/<REDACTED>/phenoShared.git`, which returns *Repository not found* for `GITHUB_TOKEN`. Workspace `Cargo.toml` only lists member `rust` — no phenoShared path dependency.
- **Fix class:** **(a) broken** — stale clone from pre–workspace-cleanup layout.
- **Repair:** Remove phenoShared checkout step.

### Conventional Commits (`ci.yml` → `commit-lint`)

- **Required vs advisory:** Advisory (not in ruleset baseline).
- **Why it fails:** `@commitlint/config-conventional` enforces lowercase subjects. Example failure: `fix: AgilePlus perf+ops+api…` → `subject must not be sentence-case`.
- **Fix class:** **(b) comply** — use `fix: agileplus perf+ops+api hardening (audit gaps)` or add scope: `fix(ci): …`.
- **Repair:** None (eco-028 commit hygiene).

### gitleaks scan (`gitleaks.yml`)

- **Required vs advisory:** Advisory; duplicate of `security.yml` → `Gitleaks` (which passes).
- **Why it fails:** Action resolution error — placeholder commit SHA does not exist. Secondary: `GITLEAKS_CONFIG: .gitleaks.toml` but repo file is `gitleaks.toml`.
- **Fix class:** **(a) broken**
- **Repair:** Use `gitleaks/gitleaks-action@v2` (same as `security.yml`); set `GITLEAKS_CONFIG: gitleaks.toml`.

### governance-index (`governance-index.yml`)

- **Required vs advisory:** Advisory.
- **Why it fails:** Regenerated index differs from committed `kitty-specs/INDEX.md` (status drift for eco-005/006/007/012/029) on PRs that never touch `kitty-specs/`.
- **Fix class:** **(a) broken** — over-broad trigger, not a spec change in the PR.
- **Repair:** Run only when `kitty-specs/**` or `tooling/governance_index.py` changes; skip verify step when generator produces no diff.

### guard (`security-guard.yml`)

- **Required vs advisory:** Advisory.
- **Why it fails:** `.pre-commit-config.yaml` hook `legacy-tooling-scan` runs `tooling/legacy-enforcement/scanner/legacy_tooling_scanner.py`, which is not vendored in-repo. `legacy-tooling-gate.yml` downloads it; guard does not.
- **Fix class:** **(a) broken**
- **Repair:** Bootstrap scanner + policy from phenotype/repos before `pre-commit/action` (mirrors legacy-tooling-gate pattern).

### policy-gate (`policy-gate.yml`)

- **Required vs advisory:** **REQUIRED** per `.github/RULESET_BASELINE.md`.
- **Why it fails:** Branch policy — `fix/*` targeting `main` without `layered-pr-exception` label.
- **Fix class:** **(b) comply** — target `stack/*` / `layer/*` / `release/*`, or add label with documented exception.
- **Repair:** None.

### pr-governance-gate (`pr-governance-gate.yml`)

- **Required vs advisory:** **REQUIRED** per ruleset baseline.
- **Why it fails:** (1) Missing PR body sections (`## Summary`, `## Stack Topology`, `## Validation`, `## Governance`, `## CI Exception`); (2) layered branch policy; (3) aggregates any other red check including broken gates above.
- **Fix class:** **(b) comply** — use PR template; fix/register spec; resolve downstream checks.
- **Repair:** None (meta-gate by design).

### sonar (`sonarcloud.yml` → job `sonar`)

- **Required vs advisory:** Advisory (`continue-on-error: true` on job, but still reports failure).
- **Why it fails:** `sonar-project.properties` is empty → scanner error: missing `sonar.projectKey`, `sonar.organization`.
- **Fix class:** **(a) broken** for config; **(c) user-gated** for `SONAR_TOKEN`.
- **Repair:** Pass `-Dsonar.projectKey=<REDACTED>_AgilePlus -Dsonar.organization=<REDACTED>` in workflow.

### SonarCloud (GitHub App check)

- **Required vs advisory:** Advisory.
- **Why it fails:** SonarCloud GitHub App + workflow need org secret `SONAR_TOKEN` and valid project binding.
- **Fix class:** **(c) user-gated**
- **How to pass:** Repo Settings → Secrets → `SONAR_TOKEN` from SonarCloud; confirm project `<REDACTED>_AgilePlus` under org `<REDACTED>`.

### spec-first (`spec-first.yml`)

- **Required vs advisory:** Advisory.
- **Why it fails:** PR body must include line `spec: eco-NNN-slug` and matching active directory under `kitty-specs/`.
- **Fix class:** **(b) comply** — register spec per eco-018 spec-first policy.
- **Repair:** None.

### Workspace Path Dependency Audit (`workspace-audit.yml`)

- **Required vs advisory:** Advisory.
- **Why it fails:** Identical broken `phenoShared` clone as Autograder (exit 128 before `workspace-audit.sh` runs).
- **Fix class:** **(a) broken**
- **Repair:** Remove phenoShared checkout; audit script only needs workspace `Cargo.toml`.

## How to make a PR pass governance (comply-needed gates)

1. **Branch targeting:** Use `stack/*` or `layer/*` integration branches, or add `layered-pr-exception` when `fix/*` must land on `main`.
2. **PR body:** Include all five sections from the governance template plus `spec: eco-NNN-your-spec-slug` for spec-first.
3. **Commits:** Lowercase conventional subjects (`type(scope): subject`); avoid Title Case in subject line.
4. **Spec registration:** Ensure `kitty-specs/<spec-id>/` exists with `spec.md`, `plan.md`, `tasks.md`, `meta.json` (`status: active`).
5. **SonarCloud:** Add `SONAR_TOKEN` org secret (user-gated).

## Workflow repairs in this PR (class a only)

- `.github/workflows/gitleaks.yml` — valid action pin + config path
- `.github/workflows/autograder.yml` — drop phenoShared clone
- `.github/workflows/workspace-audit.yml` — drop phenoShared clone
- `.github/workflows/governance-index.yml` — path filter + conditional verify
- `.github/workflows/security-guard.yml` — bootstrap legacy scanner assets
- `.github/workflows/sonarcloud.yml` — inline Sonar project key/org
