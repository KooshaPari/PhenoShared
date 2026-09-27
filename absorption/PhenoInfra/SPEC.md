# phenotype-landing — SPEC

## 1. Scope

`phenotype-landing` is a **multi-tenant landing site factory** for the Phenotype org. One monorepo hosts all public product/portfolio landing pages, consolidated from standalone repos via `git subtree` (squashed, branch-reversible). Build/runtime is Astro on Bun; each site is an independent package with its own `package.json` + lockfile, plus a root `Taskfile.yml` for SSOT recipes and a root CI matrix that fans out typecheck + build across every Astro site.

The factory must scale: adding a new landing = dropping a new directory under `sites/`, registering it in the Taskfile `SITES` var and the CI matrix, and re-running `task quality`. No cross-site coupling.

## 2. The 7 landing sites

| Path | Stack | Purpose |
|------|-------|---------|
| `sites/agileplus-landing` | Astro + Bun | AgilePlus product landing |
| `sites/byteport-landing` | Astro + Bun | BytePort **marketing** (not the app) |
| `sites/hwledger-landing` | Astro + Bun | HW Ledger landing |
| `sites/phenokits-landing` | Astro + Bun | Phenokits catalog landing |
| `sites/projects-landing` | Astro + Bun | `projects.kooshapari.com` portfolio |
| `sites/thegent-landing` | Astro + Bun | TheGent landing |
| `sites/odin-landing` | Static HTML/CSS | Odin landing (no Astro build) |

## 3. Key invariants

- One Astro site = one directory = one `package.json` + one lockfile (no hoisting across sites).
- Root has no `package.json` / no `bun.lockb`; coordination is via `Taskfile.yml` only.
- `odin-landing` is explicitly out of the Astro CI matrix and Taskfile `SITES` var.
- `AppGen` (Expo/React Native) is **not** absorbed; it is not a landing.
- Subtree pull flow: `git subtree pull --prefix=sites/<name> <remote> main --squash` keeps reversibility on a branch.
- All shared design tokens / components must live under `packages/`, not duplicated per-site.

## 4. Top gaps (2/14 compliance)

- **Compliance: 2 of 14** — only `AGENTS.md` present; no central `SPEC.md` (this file closes that), no VitePress docsite, no PRD/ADR/PLAN/USER_JOURNEYS trackers, no `docs-site/`, no `.phenotype/` SSOT config.
- **No central spec** — coordination lives in README/STATUS prose; no machine-readable manifest of site metadata (name, domain, framework, deploy target).
- **No VitePress docsite** — global Phenotype rule expects `docs-site/` per project; landing monorepo has none.
- **`packages/` and `templates/` skeletons exist but are empty** — shared components (ui, github-fetcher, design-tokens) and a generic landing template are still TODO per STATUS.md.
- **`projects-landing` still uses `gh` CLI scraping** — needs migration to GitHub API for robustness.
- **No `task quality` wired into root CI** — Taskfile exists, but `.github/workflows/ci.yml` runs its own Astro build matrix; Taskfile and CI are not unified.

## 5. Success criteria

`task quality` passes; all 6 Astro sites build via root CI; adding an 8th site requires only `sites/<name>/` + one line in `Taskfile.yml` + one matrix entry.

## v8 Phase 3 — T17 + T18 (2026-06-20)

Tightened lint configurations and Tier-2 coverage gate per ADR-040 (80% lib / 70% framework / 60% service). HOOKS_SKIP / SKIP env vars enable ad-hoc testing. OIDC trust (no PAT secrets).
