# Threat Model (STRIDE-per-component)

> **Source audit:** `FLEET-AUDIT-30-PILLAR.md` — S7 (Threat model) is the #1 P0 gap across the Phenotype fleet. PhenoHandbook lifted from S7=0 to S7=2 (wired) on 2026-06-16 via PHE-066.
> **Method:** STRIDE per-component. Each component in the system gets a row; each STRIDE category is a column.
> **Owner of this file:** ci-ops (security: ci-ops). **Review cadence:** quarterly + on any new external dependency.

## When to do this

A threat model is **wired** (score 2) when this file exists in `docs/security/threat-model.md`
and is referenced from your `README.md` or `SECURITY.md`.
It's **measured** (score 3) when a CI gate fails if the file is more than 90 days old.

## STRIDE cheat sheet

| Letter | Threat | Property violated | Question to ask |
|--------|--------|-------------------|------------------|
| **S** | Spoofing | Authentication | Can an attacker impersonate a user/system? |
| **T** | Tampering | Integrity | Can an attacker modify data or code? |
| **R** | Repudiation | Non-repudiation | Can a user deny an action they took? |
| **I** | Information disclosure | Confidentiality | Can an attacker read data they shouldn't? |
| **D** | Denial of service | Availability | Can an attacker make the system unavailable? |
| **E** | Elevation of privilege | Authorization | Can an attacker gain higher privileges? |

For each cell, mark one of: **N/A** (not applicable to this component), **low** (impact minor,
mitigation optional), **med** (mitigation required), **high** (mitigation + test required).

---

## Component inventory

List every component in your system. A component is any discrete unit that handles data
or accepts input — a service, a CLI, a database, a queue, a third-party dependency, a
network boundary, a CI workflow, even a build artifact.

Example components (adjust to your system):
- Public web frontend
- Public API
- Auth service
- Database (primary + replicas)
- Object storage
- Message queue
- Background workers
- Admin console
- CI/CD pipeline
- Third-party LLM providers
- CLI tool
- Container runtime

## Per-component threat grid

For each component, fill in the STRIDE table.

### Component: `<name>`

| Threat | Rating | Specific attack vector | Mitigation | Owner | Last reviewed |
|--------|--------|------------------------|------------|-------|---------------|
| **S — Spoofing** | low/med/high | | | | YYYY-MM-DD |
| **T — Tampering** | | | | | |
| **R — Repudiation** | | | | | |
| **I — Info disclosure** | | | | | |
| **D — DoS** | | | | | |
| **E — Elevation** | | | | | |

Repeat this block for every component.

---

## Component inventory (PhenoHandbook)

PhenoHandbook is a **VitePress-based documentation site** with a small TypeScript test
suite (vitest) and 9 GitHub Actions workflows. The components below cover the entire
attack surface: the static site, the build pipeline, the CI workflows, and the
upstream supply chain.

| # | Component | Type | Boundary |
|---|-----------|------|----------|
| 1 | VitePress static docs site | Renderer (SSG) | Public read-only web |
| 2 | GitHub Actions CI workflows (9) | Build/CI | GitHub-controlled |
| 3 | npm/vitest build pipeline | Build/test toolchain | Local + CI |
| 4 | trufflehog secret scanner | CI scanner | GitHub-controlled |
| 5 | VitePress search index (`local` provider) | Client-side index | Bundled into static site |
| 6 | GitHub Pages hosting | Public hosting | GitHub-managed |
| 7 | CODEOWNERS gate | Access control | GitHub-controlled |
| 8 | External Reusable workflow (`phenotype-org-governance`) | Reusable CI | Third-party org repo |
| 9 | Pre-commit hooks (`.pre-commit-config.yaml`) | Local pre-commit | Developer machine |

## Worked examples (PhenoHandbook)

These three components are the most security-relevant: the public docs renderer, the
CI pipeline (with mixed SHA/tag pinning), and the build pipeline.

### Component 1: VitePress static docs site (`docs/.vitepress`)

| Threat | Rating | Specific attack vector | Mitigation | Owner | Last reviewed |
|--------|--------|------------------------|------------|-------|---------------|
| **S — Spoofing** | low | Phishing sub-domain mimicking `/handbook/` on github.io | Reserved `KooshaPari/PhenoHandbook` org + no custom domain configured | infra | 2026-06-16 |
| **T — Tampering** | med | Malicious PR that injects content via the VitePress build (e.g. inline scripts in markdown) | CODEOWNERS gate; PR review required; markdownlint in `conventions.yml` | docs | 2026-06-16 |
| **R — Repudiation** | low | Authorship of doc changes | Git commit log; Co-Authored-By trailers | docs | 2026-06-16 |
| **I — Info disclosure** | low | Leaked secrets in doc content | `trufflehog.yml` CI workflow + `.pre-commit-config.yaml` local hook + `trufflehog.yml` config | security | 2026-06-16 |
| **D — DoS** | low | GitHub Pages availability | Out of scope (GitHub-managed SLA) | n/a | 2026-06-16 |
| **E — Elevation** | low | Branch protection bypass to merge to `main` | CODEOWNERS + required status checks (quality-gate, fr-coverage) | docs | 2026-06-16 |

### Component 2: GitHub Actions CI workflows (9 workflows in `.github/workflows/`)

| Threat | Rating | Specific attack vector | Mitigation | Owner | Last reviewed |
|--------|--------|------------------------|------------|-------|---------------|
| **S — Spoofing** | med | Compromised third-party GitHub Action tag (`@v6`, `@v2.4.3`, `@main`) re-tagged with malicious code | **Mixed state** — `scorecard.yml`, `legacy-tooling-gate.yml`, `trufflehog.yml` are SHA-pinned; `ci.yml`, `happy-path-precommit.yml` use `actions/checkout@v6` / `actions/setup-node@v6` tags (gap); `trufflehog` uses `@main` (gap) | ci-ops | 2026-06-16 |
| **T — Tampering** | med | Malicious workflow PR that backdoors CI | CODEOWNERS + branch protection on `main`; PR review required | ci-ops | 2026-06-16 |
| **R — Repudiation** | low | Workflow authorship repudiation | Git log of `.github/workflows/`; GitHub UI workflow history | ci-ops | 2026-06-16 |
| **I — Info disclosure** | low | Workflow logs leaking tokens / secrets | No secrets currently defined; all future secrets via GitHub Actions secrets (encrypted at rest) | security | 2026-06-16 |
| **D — DoS** | med | Workflow abuse / quota exhaustion (Actions billing is constrained for this org) | Pin to standard Linux runners; avoid cron schedules on `*:*` minutes; cap concurrency where possible | infra | 2026-06-16 |
| **E — Elevation** | med | Workflow gains write access via default `GITHUB_TOKEN` | Workflows that don't need write should declare `permissions: contents: read` (currently only `scorecard.yml` does so explicitly — gap) | ci-ops | 2026-06-16 |

### Component 3: Build pipeline (vitepress build + vitest)

| Threat | Rating | Specific attack vector | Mitigation | Owner | Last reviewed |
|--------|--------|------------------------|------------|-------|---------------|
| **S — Spoofing** | low | Typosquatted `vitepress` / `vitest` package on npm | `package.json` declares `vitepress ^1.0.0` and `vitest ^4.1.7` (latest majors at time of authoring); `overrides` pin `vite` to `6.4.2`; lockfile if present | ci-ops | 2026-06-16 |
| **T — Tampering** | med | Malicious dep transitively inlines code at install time | `package.json` `overrides` block constrains `vitepress -> vite`; dependabot.yml monitors; trufflehog catches secret exfil; build is reproducible from lockfile | ci-ops | 2026-06-16 |
| **R — Repudiation** | low | Build provenance | Build runs in GitHub Actions with logged step output; `vitest` test suite is the only quality gate today (1 test file in `tests/smoke.test.ts`) | ci-ops | 2026-06-16 |
| **I — Info disclosure** | low | Build logs containing env secrets | No env secrets in build today; if added, must come via GitHub Actions secrets, not workflow YAML | security | 2026-06-16 |
| **D — DoS** | low | VitePress build OOM on huge doc set | `docs/` is small (~hundreds of md files); build runs on standard Linux runner with default resources | infra | 2026-06-16 |
| **E — Elevation** | low | Build script postinstall runs arbitrary code | `package.json` has no `postinstall` / arbitrary install scripts; review any future dep that adds one | ci-ops | 2026-06-16 |

---

## How to lift the S7 score

- **0 → 1 (ad-hoc):** Add a `docs/security/threat-model.md` with at least one component's STRIDE table.
- **1 → 2 (wired):** Reference the threat model from `README.md` and `SECURITY.md`. Cover at least 80% of your components. Add an owner + last-reviewed column to each row.
- **2 → 3 (measured):** Add a CI gate that fails if `docs/security/threat-model.md` is older than 90 days, OR if a previously-scored component row is deleted.

## Review cadence

Review the threat model:
- **On every major release** (semver minor)
- **On any new external dependency** added
- **On any new public-facing endpoint**
- **Quarterly minimum** (a 90-day-old model is a CI failure for "measured" repos)

## Cross-references

- `docs/audits/PhenoHandbook/ACTION-PLAN.md` — PHE-066 (S7 lift task).
- `docs/audits/FLEET-AUDIT-30-PILLAR.md` — fleet-wide per-pillar distribution.
- `SECURITY.md` — vulnerability reporting policy.
- `CODEOWNERS` — gates that enforce the T (Tampering) row in component 2.
- `trufflehog.yml` + `.pre-commit-config.yaml` — controls for the I (Info disclosure) row.

## How to validate

```bash
# After writing your threat model, validate it has all 6 STRIDE rows.
# Rows in this file are formatted as `| **S — Spoofing** | ...` so we
# match `^\| \*\*S` (pipe + bold letter) — not `^\*\*S ` (bare bold).
for c in S T R I D E; do
  grep -qE "^\| \*\*$c " docs/security/threat-model.md || echo "missing $c"
done
```

If `grep` returns nothing for all 6 letters, your file is valid.

## Provenance

- **Template version:** 1.0
- **Author:** Phenotype Org holistic audit, 2026-06-16
- **Audit that produced it:** `FLEET-AUDIT-30-PILLAR.md` (S7 P0)
- **License:** Same as the parent repo
