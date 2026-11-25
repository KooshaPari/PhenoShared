# Merge Plan: PhenoLanding → Pheno

**Date:** 2026-09-15
**Source:** `<REDACTED>/zz-merge-unk-PhenoLanding` (Astro/JS/TS monorepo)
**Target:** `<REDACTED>/pheno` (Rust Cargo workspace monorepo)
**Status:** ANALYSIS ONLY — do not execute

---

## 1. Source Repository Profile (PhenoLanding)

| Attribute | Value |
|---|---|
| **Repo** | `<REDACTED>/zz-merge-unk-PhenoLanding` |
| **Size** | 2.8 MB (source only, no node_modules) |
| **Files** | 779 |
| **Primary Language** | Astro (460 KB), JavaScript (60 KB), TypeScript (31 KB), CSS (27 KB) |
| **Package Manager** | Bun |
| **Task Runner** | `just` (justfile) |
| **Description** | Monorepo for all Phenotype org landing pages |

### Sites (11 total)

| Site | Purpose | Domain Pattern |
|---|---|---|
| `agileplus-landing` | AgilePlus product page | `agileplus.<REDACTED>.com` |
| `benchora-landing` | Benchora product page | TBD |
| `byteport-landing` | BytePort product page | TBD |
| `hwledger-landing` | HWLedger product page | TBD |
| `odin-landing` | Odin product page | `odin.<REDACTED>.com` |
| `phenokits-landing` | PhenoKits product page | TBD |
| `projects-landing` | Projects showcase | TBD |
| `tasken-landing` | Tasken product page | TBD |
| `thegent-landing` | TheGent product page | TBD |
| `tokn-landing` | Tokn product page | TBD |
| `tracera-landing` | Tracera product page | TBD |

### Shared Packages (5)

| Package | Purpose |
|---|---|
| `packages/auth` | Auth middleware (TypeScript) |
| `packages/design-tokens` | Shared design tokens (ARCHIVED) |
| `packages/github-fetcher` | GitHub API data fetcher |
| `packages/site-base` | Shared Astro base config + pages |
| `packages/ui` | Shared UI components (ARCHIVED) |

### Build Pipeline

```
bun install → bun run build (per site) → Astro static output
```

### Root-Level CI/Governance Files

- `.github/workflows/ci.yml` (multi-language detect-and-build)
- `.github/workflows/coverage.yml`
- `.github/workflows/infisical.yml`
- `.github/workflows/release-npm.yml`
- `.github/workflows/scorecard.yml`
- `.github/workflows/trunk-check.yml`
- `.circleci/config.yml`
- `CODEOWNERS`
- `AGENTS.md`, `CLAUDE.md`
- `Taskfile.yml` (Task runner, not `just`)
- `deny.toml` (cargo-deny placeholder, no Rust)
- `justfile` (developer task runner)

---

## 2. Target Repository Profile (Pheno)

| Attribute | Value |
|---|---|
| **Repo** | `<REDACTED>/pheno` |
| **Size** | ~4.4 GB (including `target/` build artifacts) |
| **LOC** | 170K+ Rust |
| **Workspace Members** | 80+ crates across 6 domains |
| **Primary Language** | Rust (Cargo workspace, resolver = "2") |
| **Task Runners** | `just` (justfile), `task` (Taskfile.yml) |
| **Rust Version** | 1.86+ |

### Workspace Domains

| Domain | Crates |
|---|---|
| **Phenotype Core** | 32 crates (async-traits, cache, contracts, errors, etc.) |
| **AgilePlus** | 20 crates (api, cli, domain, events, git, grpc, etc.) |
| **EyeTracker** | 7 crates (domain, math, core, ffi, camera, inference, cli) |
| **Other** | 7 crates (bifrost, clap-ext, configra, apisync, etc.) |
| **ForgeCode** | forgecode-core |
| **Non-Rust** | `koosha-portfolio` (Astro), `docs/` (VitePress) |

### Existing Non-Rust Content in Pheno

| Directory | Type | Build System |
|---|---|---|
| `koosha-portfolio/` | Astro personal portfolio | `bun` + `astro` |
| `docs/` | VitePress documentation | `bun` + `vitepress` |
| `phenotype-infrakit/` | Has `package.json` | Unknown |
| `apps/byteport/` | Backend Rust app | Cargo |
| `apps/desktop/` | macOS entitlements | N/A |

---

## 3. Compatibility Assessment

### 3.1 Language Compatibility: INCOMPATIBLE (but coexistable)

Pheno is a **Rust Cargo workspace**. PhenoLanding is a **Bun/Node.js Astro monorepo**. These are fundamentally different ecosystems with no shared build toolchain.

**However**, Pheno already hosts non-Rust content:
- `koosha-portfolio/` is an Astro site (same stack as PhenoLanding)
- `docs/` is VitePress (JS/TS)
- These exist as standalone directories with independent `package.json` files

**Verdict: Astro sites CAN exist inside pheno as standalone directories. They do NOT need to become Cargo workspace members.**

### 3.2 Structural Compatibility: MODERATE

| Concern | Status | Detail |
|---|---|---|
| Cargo.toml workspace | OK | Landing pages have no Rust; no Cargo.toml needed |
| Root justfile | CONFLICT | Both repos have a `justfile` with different contents |
| Root Taskfile.yml | CONFLICT | Both repos have a `Taskfile.yml` |
| `.github/workflows/` | CONFLICT | PhenoLanding has 6 workflows; pheno has its own CI |
| `CODEOWNERS` | CONFLICT | Both files exist at root |
| `AGENTS.md` / `CLAUDE.md` | CONFLICT | Both files exist at root |
| `deny.toml` | MINOR | PhenoLanding has a placeholder; pheno has real config |
| `bun.lock` | NONE | PhenoLanding doesn't have root-level bun.lock (per-site) |

### 3.3 Directory Layout Compatibility: GOOD

PhenoLanding's content lives under `sites/` and `packages/`. Pheno has no `sites/` or `packages/` directory at root. The landing content can be placed under a dedicated top-level directory without structural collision.

---

## 4. Recommended Merge Strategy

### Option A: Merge as-is under `sites/landing/` (RECOMMENDED)

Move PhenoLanding's entire `sites/` and `packages/` trees into `pheno/sites/landing/`. Keep PhenoLanding's root-level config files merged into pheno's existing infrastructure.

```
pheno/
├── sites/
│   └── landing/
│       ├── sites/          # All 11 Astro landing sites
│       │   ├── agileplus-landing/
│       │   ├── benchora-landing/
│       │   ├── byteport-landing/
│       │   ├── hwledger-landing/
│       │   ├── odin-landing/
│       │   ├── phenokits-landing/
│       │   ├── projects-landing/
│       │   ├── tasken-landing/
│       │   ├── thegent-landing/
│       │   ├── tokn-landing/
│       │   └── tracera-landing/
│       ├── packages/       # Shared JS/TS packages
│       │   ├── auth/
│       │   ├── github-fetcher/
│       │   └── site-base/
│       ├── justfile         # PhenoLanding justfile (prefixed recipes)
│       ├── Taskfile.yml     # PhenoLanding Taskfile (prefixed tasks)
│       └── README.md
├── crates/                  # Existing Rust crates (unchanged)
├── koosha-portfolio/        # Existing Astro portfolio (unchanged)
├── docs/                    # Existing VitePress docs (unchanged)
└── ... (other pheno dirs)
```

### Option B: Flatten into root `sites/` directory

Place each landing site directly under `pheno/sites/` (no nested `landing/` level). This is cleaner but risks collision with future non-landing site directories.

### Option C: Keep as submodule (NOT RECOMMENDED)

Maintain PhenoLanding as a git submodule. This avoids merge conflicts but adds operational complexity and is inconsistent with how `koosha-portfolio` and `docs/` are handled.

---

## 5. File-Level Conflict Analysis

### 5.1 Root-Level Conflicts (MUST RESOLVE)

| File | PhenoLanding | Pheno | Resolution |
|---|---|---|---|
| `justfile` | Astro site build recipes | Rust workspace build recipes | **Merge**: Add landing recipes as namespaced `just` groups |
| `Taskfile.yml` | Astro CI tasks | Rust CI + dev stack tasks | **Merge**: Add landing tasks under `landing:` namespace |
| `.github/workflows/ci.yml` | Multi-language detect-and-build | Rust CI | **Replace**: PhenoLanding's detect-and-build is a superset; use it as the new CI with Rust job added |
| `.github/workflows/coverage.yml` | Exists | May or may not exist | **Merge or keep PhenoLanding's** |
| `.github/workflows/release-npm.yml` | NPM release | N/A | **Keep**: Useful for future JS packages |
| `.github/workflows/scorecard.yml` | OpenSSF Scorecard | May exist | **Keep** |
| `.github/workflows/trunk-check.yml` | Trunk linting | May exist | **Keep** |
| `.github/workflows/infisical.yml` | Secrets sync | N/A | **Keep** |
| `CODEOWNERS` | PhenoLanding owners | Pheno owners | **Merge**: Union of both files |
| `AGENTS.md` | PhenoLanding agent guide | Pheno agent guide | **Merge**: Add landing-specific sections to pheno's AGENTS.md |
| `CLAUDE.md` | PhenoLanding Claude guide | Pheno Claude guide | **Merge**: Add landing-specific sections to pheno's CLAUDE.md |
| `deny.toml` | Placeholder (no Rust) | Real cargo-deny config | **Keep pheno's**: PhenoLanding's is a no-op |
| `.circleci/config.yml` | Exists | May not exist | **Keep or migrate**: Check if pheno uses CircleCI |

### 5.2 Per-Site Conflicts (NONE EXPECTED)

Each site under `sites/` is self-contained with its own:
- `package.json` (no Cargo.toml collision)
- `astro.config.mjs`
- `src/`
- `public/`
- `.github/` (per-site workflows, only relevant if sites become standalone repos later)

**No file-level conflicts within the sites themselves.**

### 5.3 Per-Site Inner `.github/` Workflows

Each site has its own `.github/workflows/ci.yml` and `trufflehog.yml`. These are designed for standalone repos. In the merged monorepo, they become inert (GitHub only reads `.github/workflows/` from the default branch root). Options:
- **Delete them**: They won't run in the merged repo
- **Keep them for reference**: If sites are ever re-extracted
- **Convert to reusable workflows**: For site-specific CI triggered from root

---

## 6. What Files Move

### 6.1 Files to Move (PhenoLanding → Pheno)

| Source Path | Destination Path | Count |
|---|---|---|
| `sites/*` (11 site dirs) | `sites/landing/sites/*` | ~700 files |
| `packages/auth` | `sites/landing/packages/auth` | ~3 files |
| `packages/github-fetcher` | `sites/landing/packages/github-fetcher` | ~3 files |
| `packages/site-base` | `sites/landing/packages/site-base` | ~5 files |
| `packages/design-tokens` | `sites/landing/packages/design-tokens` | ~1 file |
| `packages/ui` | `sites/landing/packages/ui` | ~1 file |
| `scripts/generate-landings.mjs` | `sites/landing/scripts/` | 1 file |
| `docs/` (PhenoLanding docs) | `sites/landing/docs/` | ~6 files |
| `findings/` | `sites/landing/findings/` | 1 file |
| `justfile` | Merge into root `justfile` | 1 file |
| `Taskfile.yml` | Merge into root `Taskfile.yml` | 1 file |

### 6.2 Files to Merge (Root-Level)

| File | Action |
|---|---|
| `.github/workflows/ci.yml` | Replace with PhenoLanding's multi-lang detect-and-build, add Rust job |
| `.github/workflows/coverage.yml` | Add if missing in pheno |
| `.github/workflows/release-npm.yml` | Add to pheno |
| `.github/workflows/scorecard.yml` | Add if missing |
| `.github/workflows/trunk-check.yml` | Add if missing |
| `.github/workflows/infisical.yml` | Add to pheno |
| `CODEOWNERS` | Union merge |
| `AGENTS.md` | Append landing sections |
| `CLAUDE.md` | Append landing sections |
| `justfile` | Add landing recipe group |
| `Taskfile.yml` | Add landing task group |

### 6.3 Files to Discard (PhenoLanding)

| File | Reason |
|---|---|
| `deny.toml` | Placeholder; pheno's is real |
| `.circleci/config.yml` | Check if pheno uses CircleCI; likely redundant with GH Actions |
| `.mergify.yml` | PhenoLanding-specific; check pheno's config |
| `phenodag.db` | Database artifact; should not be in repo |
| `renovate.json` | Merge into pheno's renovate config if exists |
| `.pre-commit-config.yaml` | Merge into pheno's config |
| Root `package.json` | Does not exist in PhenoLanding (each site has own) |
| Per-site `.github/` dirs | Inert in monorepo; keep for reference or delete |

---

## 7. CI/CD Integration Plan

### 7.1 Unified CI Strategy

PhenoLanding's CI uses a **language-detection pattern**: it scans for `Cargo.toml`, `package.json`, `pyproject.toml`, `go.mod` and runs only relevant jobs. This is ideal for a polyglot monorepo.

**Recommended approach:**
1. Adopt PhenoLanding's `ci.yml` as the base
2. Add pheno's Rust-specific jobs (cargo-deny, grouped builds)
3. Add path filters to avoid running Astro CI on Rust-only changes and vice versa

### 7.2 Path-Filtered CI

```yaml
# Trigger Rust CI only when crates/ or Cargo.* change
on:
  push:
    paths:
      - 'crates/**'
      - 'Cargo.toml'
      - 'Cargo.lock'
      - 'rust-toolchain.toml'

# Trigger Landing CI only when sites/ or landing packages change
on:
  push:
    paths:
      - 'sites/landing/**'
```

### 7.3 Deployment

- **Landing pages**: Continue deploying to Vercel (each site has `vercel.json`)
- **Rust crates**: Continue existing CI/CD pipeline
- **No cross-dependency**: Landing pages don't depend on Rust crates at build time

---

## 8. Estimated Effort

| Task | Est. Time | Risk |
|---|---|---|
| Create branch, copy `sites/` and `packages/` | 15 min | Low |
| Merge root `justfile` | 20 min | Low |
| Merge root `Taskfile.yml` | 20 min | Low |
| Merge `.github/workflows/` (6 files) | 45 min | Medium |
| Merge `CODEOWNERS` | 10 min | Low |
| Merge `AGENTS.md` + `CLAUDE.md` | 30 min | Low |
| Update CI path filters | 30 min | Medium |
| Remove/discard redundant files | 10 min | Low |
| Test: `bun install` + `bun run build` for each site | 30 min | Low |
| Test: `cargo build --workspace` still works | 15 min | Low |
| Test: `just` and `task` commands work | 15 min | Low |
| Verify Vercel deployments still work | 30 min | Medium |
| Documentation update | 20 min | Low |
| **Total** | **~4.5 hours** | |

---

## 9. Risk Assessment

### 9.1 Risk Matrix

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| CI workflow conflicts break builds | HIGH | HIGH | Test CI in branch before merge; use path filters |
| `justfile` recipe collisions | MEDIUM | LOW | Namespace landing recipes under `landing:` prefix |
| Vercel deployment breaks after move | MEDIUM | HIGH | Verify `vercel.json` root detection; may need monorepo config |
| Repo size bloat (node_modules accidentally committed) | LOW | HIGH | Ensure `.gitignore` includes `node_modules/`, `bun.lock` per-site only |
| Bun runtime not available in pheno CI | LOW | MEDIUM | Add `oven-sh/setup-bun` action to CI |
| `cargo build` pulls in JS deps accidentally | VERY LOW | LOW | No `package.json` at workspace root; Cargo ignores JS |
| Merge conflicts in governance files | HIGH | LOW | Acceptable; manual resolution is straightforward |
| PhenoLanding's multi-site CI runs on every PR | MEDIUM | MEDIUM | Use path filters to limit CI scope |

### 9.2 Critical Risks

**Vercel Deployment (MEDIUM-HIGH):**
Each PhenoLanding site has its own `vercel.json` with project-specific config. When moved into a subdirectory, Vercel's automatic project detection may break. Each site may need its Vercel project reconfigured to point to the new path (`sites/landing/sites/<name>`).

**Mitigation:** Before merge, update each Vercel project's "Root Directory" setting to `sites/landing/sites/<name>`. Test deployment from the branch before merging to main.

**CI Complexity (MEDIUM):**
Pheno's current CI is Rust-only. PhenoLanding's CI is multi-language. Merging them creates a more complex CI pipeline that needs careful path filtering.

**Mitigation:** Adopt PhenoLanding's language-detection CI as the base, add pheno-specific Rust jobs, and use `paths` filters aggressively.

---

## 10. Pre-Merge Checklist

- [ ] Create branch `merge/pheno-landing` from pheno `main`
- [ ] Copy `sites/` and `packages/` from PhenoLanding into `sites/landing/`
- [ ] Merge root `justfile` (add `landing:` group)
- [ ] Merge root `Taskfile.yml` (add `landing:` namespace)
- [ ] Merge `.github/workflows/` (adopt PhenoLanding's CI, add path filters)
- [ ] Merge `CODEOWNERS` (union of both)
- [ ] Merge `AGENTS.md` + `CLAUDE.md` (append landing sections)
- [ ] Discard `deny.toml` placeholder, `phenodag.db`, `.circleci/`
- [ ] Verify `.gitignore` covers `node_modules/`, `bun.lock` (per-site)
- [ ] Run `bun install && bun run build` for each site
- [ ] Run `cargo build --workspace` to verify no breakage
- [ ] Run `just --list` and `task --list` to verify merged commands
- [ ] Test Vercel deployment from branch for 1-2 sites
- [ ] Update pheno README.md to document landing pages
- [ ] Open PR with CI passing

---

## 11. Post-Merge Considerations

### 11.1 Future: Shared CI with Rust + Astro

The unified CI can serve as a template for other polyglot merges (e.g., if Go SDKs or Python tools are absorbed later).

### 11.2 Future: Landing Page as Cargo Workspace Member?

**Not recommended.** Astro/JS projects don't benefit from Cargo workspace membership. They should remain as standalone directories with independent `package.json` files, similar to how `koosha-portfolio` and `docs/` are handled today.

### 11.3 Future: Extract Sites as Standalone Repos?

If landing pages need independent CI/CD, they can be extracted back out. PhenoLanding's current structure (each site self-contained) makes this trivial. The monorepo merge is reversible.

### 11.4 Governance: ADR for Landing Pages

Create an ADR (e.g., ADR-025) documenting:
- Landing pages live under `sites/landing/` in the pheno monorepo
- Each site is an independent Astro project with its own `package.json`
- Landing pages are NOT Cargo workspace members
- CI uses path filters to avoid running Rust CI on landing changes
- Vercel deploys from the `sites/landing/sites/<name>` path

---

## Appendix A: PhenoLanding Language Breakdown

| Language | Size | Files |
|---|---|---|
| Astro | 460 KB | 58 `.astro` files |
| JavaScript | 60 KB | 24 `.mjs` + 2 `.js` files |
| TypeScript | 31 KB | 35 `.ts` files |
| CSS | 27 KB | 12 `.css` files |
| Markdown | ~50 KB | 144 `.md` files |
| YAML/YML | ~30 KB | 89 `.yml` + 11 `.yaml` files |
| JSON | ~40 KB | 67 `.json` files |
| Other | ~10 KB | `.ico`, `.png`, `.html`, etc. |

## Appendix B: Pheno Workspace Members (80+)

See `Cargo.toml` workspace members list for the full enumeration.
Key domains: Phenotype Core (32 crates), AgilePlus (20), EyeTracker (7), Configra (6), Other (7+).

## Appendix C: Existing Pheno Non-Rust Precedent

| Directory | Stack | Package Manager | Build |
|---|---|---|---|
| `koosha-portfolio/` | Astro | bun | `astro build` |
| `docs/` | VitePress | bun | `vitepress build` |
| `phenotype-infrakit/` | JS/TS | bun/npm | Unknown |

These prove that JS/TS projects can coexist with the Rust workspace in pheno.
