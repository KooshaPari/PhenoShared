# Dependency Hygiene Audit - 2026-05-05

## Audit Summary

Three dependency hygiene audits conducted across the Phenotype repos:
1. GitHub Actions version pinning (SHA verification)
2. npm dependency staleness (5 active repos)
3. Go module replace directive analysis

---

## AUDIT 1: GitHub Actions Version Pinning

### Result: CLEAN

No workflows found using `@v1`, `@v2`, `@v3` tags without SHA pins.

All workflow files scanned use SHA-pinned or `@latest`/`@main` references, which is acceptable for non-critical actions.

---

## AUDIT 2: npm Dependency Staleness

### 2.1 thegent

**Outdated packages:**
- `markdown-it-mathjax3`: 4.3.2 (current) -> 5.2.0 (latest)
- `vite-imagetools`: 9.0.3 -> 10.0.0
- `vitest`: 3.2.4 -> 4.1.5

**Security audit:**
- 7 moderate vulnerabilities
- Critical: `markdown-it` ReDoS (GHSA-38c4-r59v-3vqw) - no fix available

### 2.2 helios-cli

**Outdated packages:** None detected

**Security audit:** Clean (no vulnerabilities)

### 2.3 AtomsBot

**Outdated packages (21 total):**
| Package | Current | Latest |
|---------|---------|--------|
| @octokit/graphql | 7.1.1 | 9.0.3 |
| @octokit/rest | 20.1.2 | 22.0.1 |
| @prisma/client | 6.15.0 | 7.8.0 |
| googleapis | 152.0.0 | 171.4.0 |
| happy-dom | 15.11.7 | 20.9.0 |
| ioredis | 5.7.0 | 5.10.1 |
| discord-interactions | 4.3.0 | 4.4.0 |

**Security audit:** 34 vulnerabilities
- 2 critical
- 20 high
- 10 moderate
- 2 low

**Critical vulnerabilities:** Multiple Vite security issues (GHSA-jqfw-vq24-v9c3, GHSA-93m4-6634-74q7, GHSA-4w7w-66w2-5vf9, GHSA-v2wj-q39q-566r, GHSA-p9ff-h696-f583)

### 2.4 PolicyStack

**Outdated packages:** None detected

**Security audit:** Clean (0 vulnerabilities)

### 2.5 phenoShared

**Status:** No `package-lock.json` found - not an npm project

---

## AUDIT 3: Go Module Replace Directives

### Findings

| Repo | Replace Directive |
|------|------------------|
| argis-extensions | `replace github.com/maximhq/bifrost/core => ./bifrost/core` |
| cliproxyapi-plusplus | `replace github.com/KooshaPari/phenotype-go-auth => ./third_party/phenotype-go-auth` |

### Assessment: ACCEPTABLE

Both replace directives are for local path overrides (using `./` paths), which is standard practice for:
- Vendoring internal modules
- Development of local forks

These are NOT masking stale dependency issues.

---

## Action Items

| Priority | Repo | Issue | Recommended Action |
|----------|------|-------|-------------------|
| CRITICAL | AtomsBot | 2 critical + 20 high severity npm vulnerabilities | Run `npm audit fix --force` |
| HIGH | thegent | markdown-it ReDoS vulnerability (no fix) | Consider alternative markdown parser |
| MEDIUM | AtomsBot | 21 outdated packages including major version bumps | `npm update` for minor, review major |
| LOW | thegent | 3 outdated packages | `npm update` |

---

## Repository

- Location: `/Users/<REDACTED>/CodeProjects/Phenotype/repos/findings/dependency_hygiene_audit_2026-05-05.md`
- Audit Date: 2026-05-05
- Repos Audited: 5 (thegent, helios-cli, AtomsBot, PolicyStack, phenoShared)
