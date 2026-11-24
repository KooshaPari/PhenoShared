# Template Centralization & Deduplication Report

**Date**: 2026-04-02
**Branch**: `chore/template-centralization-dedupe`
**Status**: In Progress

## Executive Summary

This document tracks the deduplication effort to centralize shared files across the Phenotype repos shelf. The goal is to eliminate duplicate copies of common files and establish `template-commons/` as the single source of truth.

## Deduplication Results

### Files Centralized

| File Type | Before | After | Reduction |
|-----------|--------|-------|-----------|
| `AGENTS.md` | 33+ copies | 1 canonical + symlinks | ~97% |
| `SECURITY.md` | 13 copies | 1 canonical + symlinks | ~92% |
| `.pre-commit-config.yaml` | 70+ copies | 3 canonical templates | ~96% |
| CI workflows | 16+ inline | Reusable workflows | ~94% |

### AGENTS.md Deduplication

**Before**: 33 projects had identical `AGENTS.md` files (108KB each)

**After**:
- `template-commons/AGENTS.md` is the canonical source
- 32 projects now symlink to `../template-commons/AGENTS.md`

**Projects Updated**:
```bash
# Replaced with symlinks:
BytePort, Duple, phenotype-docs-engine, Seedloom, Datamold,
Guardis, HexaType, phenotype-auth-ts, phenotype-gauge,
phenotype-nexus, Traceon, Eventra, phenotype-evaluation,
phenotype-config-ts, Logify, phenoSDK, Metron, phenotype-types,
phenotype-cli-extensions, phenotype-agent-core, Flagward,
Schemaforge, Flowra, HexaGo, KodeVibeGo, Hexacore, phenotype-xdd,
template-lang-rust, template-lang-go, template-domain-service-api,
template-domain-webapp, phenotypeActions
```

### SECURITY.md Deduplication

**Before**: 13 projects had identical `SECURITY.md` files

**After**:
- `template-commons/SECURITY.md` is the canonical source
- 12 projects now symlink to `../template-commons/SECURITY.md`

**Projects Updated**:
```bash
phenotype-dep-guard, template-domain-service-api, template-lang-mojo,
template-lang-go, template-lang-elixir-hex, template-lang-rust,
template-program-ops, template-lang-python, template-domain-webapp,
template-lang-zig, template-lang-swift, template-lang-kotlin
```

### Pre-commit Config Templates

**Before**: 70+ projects had duplicate `.pre-commit-config.yaml` files

**After**: Canonical templates created in `template-commons/pre-commit-templates/`:

| Template | Language | Hash |
|----------|----------|------|
| `rust.yaml` | Rust | Most common (42 projects) |
| `typescript.yaml` | TypeScript/JS | Second most common (21 projects) |
| `python.yaml` | Python | Third most common (17 projects) |

## Canonical Sources

### File Structure

```
template-commons/
├── AGENTS.md                          # Canonical agent rules
├── SECURITY.md                        # Canonical security policy
├── .pre-commit-config.yaml           # Standard pre-commit config
├── pre-commit-templates/
│   ├── rust.yaml                     # Rust-specific hooks
│   ├── typescript.yaml               # TypeScript-specific hooks
│   ├── python.yaml                  # Python-specific hooks
│   └── README.md
├── config-templates/
│   ├── cliff.toml.template
│   ├── codecov.yml.template
│   ├── deny.toml.template
│   └── nextest.toml.template
├── workflows/
│   ├── reusable-rust-ci.yml
│   ├── reusable-python-ci.yml
│   ├── reusable-typescript-ci.yml
│   └── reusable-security-scan.yml
└── hooks/
    ├── pre-commit
    ├── pre-push
    └── commit-msg
```

### Symlink Pattern

Projects should symlink to canonical sources:

```bash
# Example: Creating symlinks
ln -s ../template-commons/AGENTS.md AGENTS.md
ln -s ../template-commons/SECURITY.md SECURITY.md
```

## Remaining Work

### High Priority
- [ ] Verify all symlinks work correctly
- [ ] Update project documentation to reference canonical sources
- [ ] Add CI check to detect new duplicate files

### Medium Priority
- [ ] Migrate remaining projects to use reusable CI workflows
- [ ] Create additional pre-commit templates (Go, Kotlin, etc.)
- [ ] Document the symlink update process for new projects

### Low Priority
- [ ] Create tooling to automate symlink creation
- [ ] Add pre-commit hook to validate symlinks

## Verification Commands

```bash
# Check for remaining duplicate AGENTS.md files
find . -maxdepth 2 -name "AGENTS.md" -type f -exec md5sum {} \; | awk '{print $1}' | sort | uniq -c | sort -rn | head

# Check for duplicate SECURITY.md files
find . -maxdepth 2 -name "SECURITY.md" -type f -exec md5sum {} \; | awk '{print $1}' | sort | uniq -c | sort -rn | head

# List all symlinks to template-commons
find . -maxdepth 2 -name "AGENTS.md" -type l 2>/dev/null
find . -maxdepth 2 -name "SECURITY.md" -type l 2>/dev/null

# Verify symlink targets
readlink -f ./BytePort/AGENTS.md
```

## Rollback Instructions

If you need to rollback these changes:

```bash
# For AGENTS.md
rm ./PROJECT/AGENTS.md
# Copy from git history or template-commons:
git checkout HEAD~1 -- ./PROJECT/AGENTS.md

# For SECURITY.md
rm ./PROJECT/SECURITY.md
git checkout HEAD~1 -- ./PROJECT/SECURITY.md
```

## References

- Previous analysis: `docs/INFRASTRUCTURE_CONSOLIDATION_ROADMAP.md`
- Template-commons: `template-commons/README.md`
- CI workflows: `template-commons/.github/workflows/`
