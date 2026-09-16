# CI Trigger Gap Audit — 2026-05-05

## Summary

Scanned 97 repos in `/Users/<REDACTED>/CodeProjects/Phenotype/repos`. The "97 repos have manual-only workflows" context refers to worktree directories and non-code directories — these are expected to have no workflows. The actual audit scope is code-bearing repos.

## Finding: Repos With Zero Workflows But Buildable Code

These repos had source files but no CI workflows at all:

| Repo | Source Files | Build System | Priority | Status |
|------|-------------|--------------|----------|--------|
| `pheno-cli/` | 50 Go files | `go.mod` present | **HIGH** | **RESOLVED** — CI added |
| `PhenoEvents/` | 13 files | submodule (`pheno-events`) | **LOW** |
| `PhenoSchema/` | 23+ files | spec/layout repo | **LOW** |

Repos with 0 source files (placeholders/stubs): `PhenoContracts/`, `PhenoControl/`, `portage-adapter-core/`

## Finding: Repos With Partial CI Coverage (Manual-Only Workflows)

These repos have workflows but some are `workflow_dispatch`/`schedule`-only (no push/PR triggers):

### High Priority (10+ missing triggers)

| Repo | Missing Triggers | Total Workflows | Gap % |
|------|-----------------|-----------------|-------|
| `cliproxyapi-plusplus/` | 15 | 25 | 60% |
| `phenoShared/` | 15 | 33 | 45% |
| `helios-cli/` | 12 | 36 | 33% |
| `helioscope/` | 15 | 51 | 29% |
| `pheno/` | 11 | 48 | 23% |
| `HexaKit/` | 11 | 51 | 22% |
| `PhenoDevOps/` | 6 | 41 | 15% |

### Medium Priority (3-9 missing triggers)

| Repo | Missing Triggers | Total Workflows | Gap % |
|------|-----------------|-----------------|-------|
| `portage/` | 2 | 29 | 7% |
| `Tokn/` | 2 | 28 | 7% |
| `phenoDesign/` | 3 | 11 | 27% |
| `Tracera/` | 3 | 38 | 8% |
| `phenotype-tooling/` | 3 | 13 | 23% |
| `phenoData/` | 1 | 14 | 7% |
| `PhenoKits/` | 1 | 13 | 8% |
| `PhenoObservability/` | 2 | 17 | 12% |
| `Sidekick/` | 1 | 12 | 8% |

### Low Priority (1-2 missing triggers)

`Configra/` (2), `Conft/` (1), `dinoforge-packs/` (1), `Eidolon/` (1), `forgecode/` (2), `heliosApp/` (2), `HeliosLab/` (1), `MCPForge/` (1), `ObservabilityKit/` (1), `Paginary/` (1), `Parpoura/` (1), `PhenoProject/` (1), `phenotype-journeys/` (1), `phenotype-org-audits/` (1), `vibeproxy/` (1)

## Special Case: phenotype-shared

`phenotype-shared/` had 1 workflow (`.github/workflows/sbom-refresh.yml`) but it was **schedule-only** (`cron: '0 0 1 * *'`) — no push/PR triggers. This is a Rust crate (`crates/phenotype-migrations/`). **RESOLVED** — push/PR CI workflow added.

## Finding: Non-Code Directories (Expected Zero CI)

The following are worktrees, archives, spec repos, and infrastructure directories — zero CI is expected and correct:

- All `*-wtrees/` directories (feature worktrees, not integration targets)
- `_archived/`, `__pycache__/`, `node_modules/`, `target/`
- `bdd-integration/`, `docs/`, `findings/`, `fleet-audit/`, `kitty-specs/`
- `pheno-cli/` — **RESOLVED** — Go CI workflow added
- `pheno-wtrees/`, `rust/`, `scripts/`, `proto/`, `python/`, `templates/`

## Actions Taken

1. **`pheno-cli/`** — Added `.github/workflows/ci.yml` with push/PR triggers. Go 1.24 build + test + staticcheck lint.
2. **`phenotype-shared/`** — Added `.github/workflows/ci.yml` with push/PR triggers. Cargo test + clippy + cargo-deny advisory check. (Note: the existing `sbom-refresh.yml` is intentionally schedule-only.)

## Remaining Recommendations

1. **Top partial-CI repos**: Prioritize `cliproxyapi-plusplus` (15/25), `phenoShared` (18/33), `helios-cli` (24/36), `helioscope` (36/51) for manual workflow conversion to push/PR triggers.
2. **PhenoControl/PhenoContracts**: Deprecate or implement — currently empty placeholders.
3. **thegent** (39/40) and **PhenoDevOps** (35/41): Both have comprehensive CI. The 1-6 missing triggers are likely intentional schedule/manual workflows.

## Methodology

```bash
# Inventory all workflows with push/PR triggers
for r in */; do
  has_ci=$(find "$r/.github/workflows" -name "*.yml" -exec grep -l "push\|pull_request" {} \; 2>/dev/null | wc -l | tr -d ' ')
  total=$(find "$r/.github/workflows" -name "*.yml" 2>/dev/null | wc -l | tr -d ' ')
  [ "$total" -gt 0 ] && echo "$r: $has_ci/$total have push/PR triggers"
done
```

Audit date: 2026-05-05
