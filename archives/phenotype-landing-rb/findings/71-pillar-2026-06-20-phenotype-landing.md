# 71-Pillar Cycle 4: phenotype-landing

**Date**: 2026-06-20
**Project**: phenotype-landing (Monorepo of Phenotype org landing pages)
**Stack**: Astro 6, Bun, TypeScript, Tailwind (per sub-package)
**Evaluator**: Forge-agent (automated)
**Schema**: 71-Pillar Cycle 4 (0–3 per domain)

---

## Scoring Summary

| # | Domain | Score (0–3) | Verdict |
|---|--------|-------------|---------|
| 1 | Architecture | 2 | Adequate — solid monorepo layout, packages/ skeletons exist but are sparse, no SSOT config |
| 2 | Performance | 2 | Adequate — Astro static output is inherently fast, no dedicated perf tooling or budgets |
| 3 | Quality | 1 | Weak — typecheck + build only; **no tests, no linter, no test framework** |
| 4 | DX | 2 | Adequate — Taskfile + justfile, clear agent docs; no dev container / nix / asdf |
| 5 | UX | 2 | Adequate — shared components + design tokens exist; no a11y tooling, no i18n, no theme |
| 6 | Security | 1 | Weak — SECURITY.md policy exists; **no SAST, no dep scanning, no secrets check** |
| 7 | Observability | 0 | Absent — **no monitoring, no analytics, no error tracking, no uptime checks** |
| 8 | Documentation | 2 | Adequate — AGENTS, CLAUDE, STATUS, SPEC, CONTRIBUTING all present; no VitePress docsite, no ADRs |
| 9 | Governance | 2 | Adequate — CI matrix build, CODEOWNERS, CONTRIBUTING; no automated release, no Dependabot, no PR templates |

**Total Score**: 12 / 27
**Mean Score**: 1.33

---

## Detailed Assessment

### 1. Architecture — Score: 2

**Strengths:**
- Astro 6 + Bun monorepo via `git subtree` with reversible branches
- 7 landing sites isolated under `sites/` — each independent `package.json` + lockfile
- Root has no `package.json` (by design — coordination via `Taskfile.yml` only)
- `packages/` directory with three shared packages scaffolded (ui, design-tokens, github-fetcher)
- `templates/landing/` exists as a generic landing template
- `odin-landing` correctly excluded from Astro CI matrix
- Clear separation of static HTML (odin) vs Astro (all others)

**Weaknesses:**
- No `.phenotype/` SSOT (single-source-of-truth) configuration
- `packages/` are sparsely populated — `github-fetcher/src/index.ts` exists but is thin; `design-tokens` has only `tokens.css` and `tailwind.config.mjs`; `ui` has 6 components but no tests
- No automated factory flow to add a new landing (currently manual: create dir + add to Taskfile + CI matrix)

---

### 2. Performance — Score: 2

**Strengths:**
- Astro generates static HTML by default — zero JS runtime for marketing pages
- Each site is lean: independent dependency sets, no hoisting
- Build artifacts are plain HTML/CSS

**Weaknesses:**
- No image optimization pipeline configured
- No performance budget or Lighthouse CI
- No bundle analysis tooling (no `vite-bundle-analyzer` or similar)
- No caching strategy documented (CDN, headers, etc.)
- No Core Web Vitals tracking

---

### 3. Quality — Score: 1

**Strengths:**
- `bunx astro check` runs in CI for type safety
- `task quality` gates: check → build → lint (lint = astro check again)
- CI matrix builds all 6 Astro sites

**Weaknesses:**
- **No test infrastructure whatsoever** — no unit, integration, E2E, or visual regression tests
- No test framework installed (no Vitest, Playwright, etc.)
- `lint` task is an alias for `astro check` — no ESLint, Prettier, or similar
- No pre-commit hooks (lint-staged, husky)
- No code coverage tracking
- SPEC.md notes "2 of 14" compliance — most governance/quality items missing

---

### 4. DX (Developer Experience) — Score: 2

**Strengths:**
- Dual task runners: `Taskfile.yml` and `justfile` for local commands
- Clear `sites/<name>/README.md` or root README with per-site instructions
- Comprehensive agent instructions in `AGENTS.md` and `CLAUDE.md`
- Quick start works: `bun install && bun run dev`
- No root `package.json` means no accidental hoisting surprises

**Weaknesses:**
- No dev container / `.devcontainer/` config
- No `.nvmrc`, `.node-version`, or `asdf` tool-versions file (Node version is hardcoded in CI only)
- No `make` or alternative entry point beyond task/just
- No hot-reload customization documented

---

### 5. UX (User Experience) — Score: 2

**Strengths:**
- Shared UI components in `packages/ui/`: CTA, Features, Footer, GitHubStats, Header, Hero
- Design tokens package with `tokens.css` and `tailwind.config.mjs`
- Tailwind CSS configured per sub-package
- `projects-landing` has brand, koosha pages beyond standard landing

**Weaknesses:**
- No accessibility (a11y) tooling or audit process (no axe-core, no Lighthouse CI)
- No internationalization (i18n) support
- No dark mode / theme toggling
- No responsive design verification in CI
- Component quality and visual consistency not validated automatically
- No user research or usability testing artifacts

---

### 6. Security — Score: 1

**Strengths:**
- `SECURITY.md` with vulnerability reporting process (72h ack, 7d triage)
- CI pins Actions to commit SHAs (supply-chain hardening)
- `CODEOWNERS` restricts sensitive paths
- Static sites = small attack surface (no server-side execution)

**Weaknesses:**
- **No SAST/DAST scanning**
- **No dependency vulnerability auditing** (no `bun audit`, no `npm audit` in CI, no Dependabot)
- **No secrets scanning** (no `trufflehog`, `gitleaks`, or GitHub secret scanning enabled)
- `deny.toml` exists but is `cargo-deny`-specific, irrelevant for this JS/TS stack
- No Content-Security-Policy headers or SRI configured
- No automated supply-chain checks beyond SHA-pinned Actions

---

### 7. Observability — Score: 0

**Strengths:**
- None identified

**Weaknesses:**
- **No monitoring or alerting** for deployed sites
- **No analytics** (no Plausible, Fathom, Umami, GA, etc.)
- **No error tracking** (no Sentry, Rollbar, etc.)
- **No uptime monitoring** (no Upptime, Better Uptime, etc.)
- **No structured logging** — CI build output is the only signal
- **No dashboard** for site health or deployment status
- Even basic build-failure notifications are absent

---

### 8. Documentation — Score: 2

**Strengths:**
- `AGENTS.md` — agent governance and rules
- `CLAUDE.md` — per-agent project instructions
- `STATUS.md` — work state and progress tracker
- `SPEC.md` — detailed spec with gaps identified
- `README.md` — monorepo layout and setup docs
- `CONTRIBUTING.md` — contribution workflow
- `SECURITY.md` — vulnerability reporting
- `CODE_OF_CONDUCT.md` — community standards
- Per-site `CHANGELOG.md` in each landing directory
- `docs/` directory with `boundary/`, `intent/`, `specs/` subdirectories

**Weaknesses:**
- **No VitePress/GitBook docsite** (required by org convention per SPEC.md)
- No ADR (Architecture Decision Record) tracking
- No PRD (Product Requirements Document)
- No API documentation (for github-fetcher package)
- No deployment/ops runbook
- `docs/` directories are nearly empty (boundary and intent have no files)

---

### 9. Governance — Score: 2

**Strengths:**
- GitHub Actions CI with matrix build for all sites
- `CODEOWNERS` file in root
- `CONTRIBUTING.md` with conventional commit prefixes and PR workflow
- `Taskfile.yml` as SSOT for quality gates
- Branch protection implied (PRs against main)
- Pinned CI Actions to commit SHAs

**Weaknesses:**
- No automated release/changelog pipeline
- No Dependabot or Renovate configured
- No issue templates (bug report, feature request)
- No PR template
- No DCO or sign-off enforcement
- CI and Taskfile are not unified — `task quality` is not wired into CI
- No stale-issue/PR management

---

## Domain Scores at a Glance

```
Architecture    ██████░░░░ 2/3
Performance     ██████░░░░ 2/3
Quality         ███░░░░░░░ 1/3
DX              ██████░░░░ 2/3
UX              ██████░░░░ 2/3
Security        ███░░░░░░░ 1/3
Observability   ░░░░░░░░░░ 0/3
Documentation   ██████░░░░ 2/3
Governance      ██████░░░░ 2/3
─────────────────────────────────
Total           ████░░░░░░ 12/27 (mean 1.33)
```

---

## Lowest-Scoring Pillars (Priority Issues)

| Rank | Pillar | Score | Gap |
|------|--------|-------|-----|
| **P0** | Observability | 0 | No monitoring, analytics, error tracking, or uptime checks whatsoever |
| **P1** | Quality | 1 | No test infrastructure, no linter, no pre-commit hooks |
| **P2** | Security | 1 | No SAST, no dependency scanning, no secrets detection |

---

*Generated by Forge-agent. Schema: 71-Pillar Cycle 4.*
