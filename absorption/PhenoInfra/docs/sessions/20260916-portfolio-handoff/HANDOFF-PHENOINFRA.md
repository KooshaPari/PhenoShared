# Handoff: PhenoInfra Portfolio (Chat 1 - Current Scope)

**Date:** 2026-09-16
**Scope:** PhenoInfra, PhenoTooling, cross-consumption, landing pages, releases

---

## Completed Work

### Landing Pages (37/37 deployed)
- All 37 sites scaffolded in `PhenoInfra/sites/<slug>-landing/`
- All deployed to Vercel and promoted to production
- All have real content (83-355 lines of Astro)
- **BLOCKER:** CNAME DNS records needed: `<slug>.phenotype.space → cname.vercel-dns.com`
- Cloudflare API token does NOT have access to phenotype.space zone (only pheno.studio)
- Wrangler OAuth token can list zones but can't write DNS
- Need: Cloudflare API token with Zone:DNS:Edit for phenotype.space

### Cross-Consumption (5 repos wired)
All wired to PhenoInfra shared infrakit crates (rev e001322):
- **Tracera**: phenotype-crypto, phenotype-telemetry, phenotype-git-core, phenotype-health, phenotype-observability (pushed to main ✓)
- **Substrate**: phenotype-crypto, phenotype-health, phenotype-observability, phenotype-policy-engine, phenotype-mcp (on remote main ✓)
- **HeliosLab**: phenotype-crypto, phenotype-health, phenotype-observability, phenotype-state-machine (pushed to main ✓)
- **ShareCLI**: phenotype-crypto, phenotype-health, phenotype-observability, phenotype-state-machine (pushed to main ✓)
- **PhenoShared** (formerly phenoAI→pheno→PhenoShared): Already had 6 refs on main ✓

### Pine Absorption
- 5 crates copied from <REDACTED>/Pine → PhenoTooling/crates/pine-*
- pine-core, pine-compat, pine-loader, pine-nvms, pine-syscall (6674 lines)
- All compile clean in PhenoTooling workspace
- Pine standalone repo README updated: "absorbed — canonical: PhenoTooling/crates/pine-*"

### Releases
- **NanoVMS v1.1.0**: GitHub release with 3 binaries (linux-amd64, darwin-arm64, darwin-amd64, 2.3MB each)
  https://github.com/<REDACTED>/PhenoTooling/releases/tag/v1.1.0-nanovms
- **BytePort v1.0.0**: Universal binaries from CI (DMG, .app.tar.gz, Windows, Linux)
  https://github.com/<REDACTED>/BytePort/releases/tag/v1.0.0

### CI/CD
- Nightly CVP CI workflow committed to PhenoInfra: `.github/workflows/cvp-nightly.yml`

### PhenoInfra Assessment
- Overall: 71/100
- Code Quality: 70 (157 Rust files, 21k lines, 484 tests, 28 infrakit crates)
- Documentation: 80 (32 ADRs, 70-line README, 257-file docs/atlas)
- CI/CD: 75 (33 GitHub Actions workflows)
- Architecture: 78 (clean workspace monorepo)
- Security: 60 (no visible dep audit)
- Release Readiness: 65 (alpha, no versioned releases)
- Test Coverage: 72 (484 tests)

### docs-3 Atlas
- 257-file portfolio atlas integrated into PhenoInfra/docs/atlas/
- 175 unit tests ALL PASS

---

## Remaining Work

1. **CNAME DNS** (BLOCKED on user providing correct CF API token for phenotype.space)
2. **Vercel production domains** (after CNAME propagation)
3. **CVP for Tracera, PhenoAI/PhenoShared** (evidence not yet generated)
4. **Dependabot alerts** on several repos (HeliosLab: 5 vulns, Tracera: 33 vulns)

---

## Key Files
- `PhenoInfra/sites/scaffold_landings.py` — reusable scaffold script (29 repos, 243 lines)
- `PhenoInfra/sites/deploy_all.sh` — bulk Vercel deploy script
- `PhenoInfra/.github/workflows/cvp-nightly.yml` — nightly evidence CI
- `PhenoTooling/Cargo.toml` — workspace with 97+ crates + pine-* + eyetracker-*
- `~/Downloads/docs-3/` — 257-file portfolio atlas (also in PhenoInfra/docs/atlas/)

---

## Repo Name Changes
- `phenoAI` → `pheno` → `PhenoShared` (GitHub repo)
- Local directory still called `PhenoAI`, remote URL updated to `PhenoShared.git`
