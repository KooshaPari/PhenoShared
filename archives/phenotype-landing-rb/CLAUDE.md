# CLAUDE.md — phenotype-landing

## Overview

- **Repo**: `KooshaPari/phenotype-landing` — monorepo of Phenotype marketing/landing sites.
- **Stack**: Astro 6, Bun, TypeScript, Tailwind (per sub-package). `odin-landing` is static HTML only.
- **Owner**: Phenotype org / KooshaPari.

## Layout

Work inside the relevant `*-landing/` subdirectory. Do not change unrelated landings in the same PR.

## Commands (typical Astro package)

```bash
cd <package>-landing
bun install
bun run dev
bunx astro check
bun run build
```

## Conventions

- Match existing sub-package patterns (workflows, `CLAUDE.md`, governance docs).
- Additive changes only unless explicitly requested.
- Branch from `main`; use PRs — do not push directly to `main`.
