<!-- AI-DD-META:START -->
<!-- This repository is planned, maintained, and managed by AI Agents only. -->
<!-- Slop issues are expected and intentionally present as part of an HITL-less -->
<!-- /minimized AI-DD metaproject of learning, refining, and building brute-force -->
<!-- training for both agents and the human operator. -->
![Downloads](https://img.shields.io/github/downloads/KooshaPari/phenotype-landing/total?style=flat-square&label=downloads&color=blue) [![AI slop inside](https://sladge.net/badge.svg)](https://sladge.net)
![GitHub release](https://img.shields.io/github/v/release/KooshaPari/phenotype-landing?style=flat-square&label=release)
![License](https://img.shields.io/github/license/KooshaPari/phenotype-landing?style=flat-square)
![AI-Slop](https://img.shields.io/badge/AI--DD-Slop%20Expected-orange?style=flat-square)
![AI-Only-Maintained](https://img.shields.io/badge/Planned%20%26%20Maintained%20by-AI%20Agents%20Only-red?style=flat-square)
![HITL-less](https://img.shields.io/badge/HITL--less%20AI--DD-metaproject-yellow?style=flat-square)

> ⚠️ **AI-Agent-Only Repository**
>
> This repo is **planned, maintained, and managed exclusively by AI Agents**.
> Slop issues, rough edges, and AI artifacts are **expected and intentionally
> present** as part of an **HITL-less / minimized AI-DD** metaproject focused
> on learning, refining, and brute-force training both the agents and the
> human operator. Bug reports and contributions are still welcome, but please
> expect AI-generated code, comments, and documentation throughout.
<!-- AI-DD-META:END -->
## Work State

| Field | Value |
|---|---|
| Last commit | 2026-06-08 |
| Open issues | 0 |
| Open PRs | 0 |
| Focus | Astro+Bun monorepo landing sites |

Progress: ███████░░░ 70%

# phenotype-landing

Monorepo of Phenotype org public landing sites (Astro + Bun), consolidated from individual repos via `git subtree` (squashed merges; reversible on a branch).

## Layout

All deployable sites live under `sites/<name>/`. Each directory is an independent Astro (or static) package with its own `package.json`, lockfile, and CI in that subtree.

| Path | Site / purpose |
|------|----------------|
| `sites/agileplus-landing` | AgilePlus product landing |
| `sites/byteport-landing` | BytePort **marketing** landing (not the BytePort app repo) |
| `sites/hwledger-landing` | HW Ledger landing |
| `sites/phenokits-landing` | Phenokits catalog landing |
| `sites/projects-landing` | Projects hub landing |
| `sites/tasken-landing` | Tasken task orchestration landing |
| `sites/tracera-landing` | Tracera requirements traceability landing |
| `sites/thegent-landing` | TheGent landing |
| `sites/odin-landing` | Odin static landing (HTML/CSS, no Astro build) |

**Not absorbed:** `AppGen` — Expo/React Native app scaffold (`expo`, `react-native`), not an Astro landing.

## Per-site development

```bash
cd sites/<name>
bun install
bun run dev    # or see site README
```

## Vercel Deployments

The following sites are configured for Vercel deployment. Each has a `vercel.json` at the site root:

| Site | Vercel Config | phenotype.space URL | Status |
|------|---------------|-------------------|--------|
| `sites/tracera-landing` | ✓ `vercel.json` | `https://phenotype.space/tracera` | Astro + Bun |
| `sites/agileplus-landing` | ✓ `vercel.json` | `https://phenotype.space/agileplus` | Astro + Bun |
| `sites/byteport-landing` | ✓ `vercel.json` | `https://phenotype.space/byteport` | Astro + Bun |
| `sites/tokn-landing` | ✓ `vercel.json` | `https://phenotype.space/tokn` | Astro + Bun |

Each `vercel.json` specifies:
- `framework: "astro"`
- `buildCommand: "bun run build"`
- `outputDirectory: "dist"`
- `installCommand: "bun install"`

Deploy a site to Vercel:
```bash
cd sites/<name>
vercel --prod
```

Or connect the repo to Vercel Dashboard for automatic deployments on push to `main`.

## Root CI

`.github/workflows/ci.yml` runs Astro typecheck + build for the eight Bun/Astro packages under `sites/` on `main` and PRs.

## Subtree updates (optional)

To pull upstream from a source landing repo after merge:

```bash
git subtree pull --prefix=sites/<name> https://github.com/KooshaPari/<name>.git main --squash
```

## License

MIT — see [LICENSE](LICENSE).
