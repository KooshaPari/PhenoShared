# Spec 008: phenodag absorption (PM/cockpit/portfolio concerns)

> Absorbs: phenodag v0.3.0 (https://github.com/KooshaPari/phenodag)
> Sponsor decision: D3 = YES (thin redirector for 1 release, then archive phenodag).
> Date: 2026-07-05
> Source: `docs/sessions/2026-07-05-polyrepo-portfolio-strategy/03-audits/03-phenodag-absorption-spec.md`

## Scope (this spec)

This spec absorbs the **PM/cockpit/portfolio** concerns from phenodag into
AgilePlus: the preset corpora, the multi-project coordination surface, and
the conventional-commits / branch hygiene. The DAG/queue/atomic-claim/lease/dedup
machinery goes to Tracera spec 008.

## FR table

| FR | Title | Source (phenodag) | Target (AgilePlus) | Notes |
|---|---|---|---|---|
| AP-PHENO-001 | YAML preset loader | `phenodag.go` + `gopkg.in/yaml.v3` | `crates/agileplus-core/src/presets/` | port + extend (Go -> Rust) |
| AP-PHENO-002 | 4 shipped presets (v3-180/melosviz-185/agileplus-50/tracera-50) | `phenodag.go` presets | `crates/agileplus-core/src/presets/corpora/` | port + refresh |
| AP-PHENO-003 | Fill (auto-task generation) | `phenodag.go` fill | `crates/agileplus-core/src/presets/fill.rs` | port |
| AP-PHENO-004 | Multi-project dashboard view | derived from `phenodag.go` status | `crates/agileplus-dashboard/src/views/fleet_dag.rs` | new view |
| AP-PHENO-005 | Conventional commits enforcement | implicit in phenodag presets | `crates/agileplus-core/src/conventional_commits.rs` | new |
| AP-PHENO-006 | Branch hygiene / PR policy | implicit in phenodag | `crates/agileplus-core/src/branch_hygiene.rs` | new |
| AP-PHENO-007 | Cross-repo fleet inventory | derived from `phenodag.go` scan | `crates/agileplus-core/src/fleet/inventory.rs` | new |

## Phased migration

| Phase | What | Effort | Risk |
|---|---|---|---|
| P1 | Port AP-PHENO-001, AP-PHENO-002 (YAML preset + 4 corpora) | 1-2 PRs | low |
| P2 | Port AP-PHENO-003 (fill) | 1 PR | low |
| P3 | Add AP-PHENO-004 (fleet DAG dashboard view) | 1-2 PRs | medium |
| P4 | Add AP-PHENO-005, AP-PHENO-006 (commits, branches) | 1-2 PRs | low |
| P5 | Add AP-PHENO-007 (cross-repo fleet inventory) | 1 PR | low |
| P6 | Archive `phenodag` repo (coordinated with Tracera P6) | 1 commit | low |

Total: ~5-8 PRs over 2-3 weeks.

## Why these go to AgilePlus (not Tracera)

AgilePlus is the **PM/cockpit** spine. The preset corpora, multi-project
coordination, conventional-commits enforcement, and branch hygiene are
PM concerns: they govern *how* work happens, not *what* work is happening.
Trace concerns (DAG/queue/claim/dedup) are in Tracera spec 008.

## Cross-references

- Tracera spec 008: phenodag absorption (DAG/queue/atomic-claim/lease/dedup)
- phenodag repo: https://github.com/KooshaPari/phenodag (will be archived)
- phenodag ADR-dedup-baseline: https://github.com/KooshaPari/phenodag/blob/main/docs/adr/ADR-dedup-baseline.md
- polyrepo portfolio strategy session: `docs/sessions/2026-07-05-polyrepo-portfolio-strategy/`

## Sign-off

- Spec author: root manager (polyrepo portfolio strategy 2026-07-05)
- AgilePlus team: TBD (this is a spec-level request, not yet a coding PR)
- Phenodag consumers: see the 1-release redirector PR for migration timing
