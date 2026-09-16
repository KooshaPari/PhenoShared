# helioscope deletion package

Date: 2026-06-20
Decision: DELETE
Confidence: medium-high

## Executive decision

helioscope can be deleted after preservation. The GitHub repo description explicitly marks it SUPERSEDED and points to KooshaPari/helios-cli as the canonical Phenotype Helios CLI fork. The active target helios-cli has the final HeliosCLI artifacts on main; the local target branch chore/absorb-helioscli-final-2026-06-20 was pushed and has zero divergence from origin/main. Residual helioscope local work is preserved here as patchsets.

## Absorption matrix

| Source Item | Source Evidence | Category | Source State | Target Repo | Target Evidence | Status | Deletion Justification | Risk if Deleted | Required Action |
|-------------|-----------------|----------|--------------|-------------|-----------------|--------|------------------------|-----------------|-----------------|
| Codex/Helios CLI fork source | helioscope/codex-rs, codex-cli, Cargo.toml | Public Rust/CLI source | implemented/fork | helios-cli | helios-cli/codex-rs, codex-cli, Cargo.toml | SUPERSEDED_PARITY | Target is canonical successor and contains the fork source tree | low-medium; fork history loss mitigated by target | none |
| Helios harness crates | helioscope/codex-rs plus harness-related docs/specs | Rust crates/framework | implemented | helios-cli | helios-cli/crates/harness_* and docs/specs | SUPERSEDED_BETTER | Target reorganizes Helios CLI as canonical multi-runtime CLI with harness crates | low | none |
| TUI renderer optimization specs | helioscope/.agileplus/specs and docs/specs/001-codex-tui-renderer-optimization | Specs | docs-only/attempted | helios-cli and phenotype-registry | helios-cli docs/specs plus source-specs here | DONE | Specs retained in target/docs and copied to registry | low | none |
| Chat composer decomposition spec | helioscope/docs/specs/002-chat-composer-decomposition/spec.md | Specs | docs-only | helios-cli and phenotype-registry | helios-cli docs/specs and source-specs here | DONE | Spec preserved | low | none |
| helioscope supersession record | GitHub description SUPERSEDED, docs/rationalization/helioscope-absorption.md | Governance | deprecated | helios-cli/phenotype-registry | helios-cli docs/rationalization and this package | INTENTIONALLY_DEPRECATED | Source explicitly points to helios-cli as canonical successor | low | none |
| helioscope local WIP branch | local branch wip/2026-06-18-helioscope-local | Branch-only work | branch-only | phenotype-registry | patches/local-wip-branch.patch | DONE | Local-only commits preserved before deletion | medium | none |
| helioscope staged Cargo diff | staged Cargo.toml/Cargo.lock in local main | Local dirty work | local-only/staged | phenotype-registry | patches/staged-cargo-diff.patch | DONE | Dirty staged diff preserved as binary-capable patch | medium | none |
| Generic spec-kitty command scaffolds | .claude/.codex/.archive command files | Tooling scaffold | scaffold | phenotype-registry | source-specs for actual specs; command scaffolds not copied | NO_MERIT | Generic command wrappers are not helioscope domain artifacts | low | none |

## Gaps and exceptions

No LAST_RESORT_EXCEPTION remains. This deletion package does not delete helios-cli; it is the active canonical target.

## Final deletion recommendation

DELETE helioscope after this registry PR merges. Remove the local helioscope clone after remote deletion.
