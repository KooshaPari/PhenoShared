# PhenoInfra

- **Source**: https://github.com/KooshaPari/PhenoInfra
- **Absorbed**: 2026-09-27
- **Disposition**: ABSORB → `absorption/PhenoInfra/`
- **Source commit**: `ecf486cab18b8e84213838d497a39ea3a94aca71` (2026-09-16)
- **Canonical owner**: this repo (PhenoShared / phenoAI)

## Summary

Compute/Infra consolidation monorepo (2537 files, 28 MB source): shared crates,
IaC, landing pages, ADRs, validation notes. Source repo was **already archived**
on GitHub before absorption.

## Action taken

- Source copied to `absorption/PhenoInfra/` (no `.git`).
- **Not** wired into the root Cargo workspace — snapshot archive only; the
  absorbed tree declares its own nested `[workspace]` and is inert.
- `PROVENANCE.md` written at the absorption root.
- Source GitHub repo remains **archived** (archived=true).
