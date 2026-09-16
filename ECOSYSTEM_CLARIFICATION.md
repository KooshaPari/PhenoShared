# Ecosystem Clarification — `phenotype-*infra*` siblings (not duplicates)

_2026-09-01 audit note — supersedes the Tier-3-P3-INFRA-CLUSTER proposal which incorrectly assumed these 3 repos were the same domain._

## Three repos, three distinct domains

| Repo | Primary language | Domain | Canonical consumer |
|---|---|---|---|
| `KooshaPari/phenotype-infra` | Rust (workspace) | **Compute / VM isolation** — nanovms-core (Go → C-static), nvms-ffi, pheno-compose, pheno-config | Apps that need WASM/gVisor/Firecracker micro-VMs (3-tier isolation) |
| `KooshaPari/phenotype-fleet-ops` | YAML/justfile/Markdown | **Reusable CI/CD + ops governance** — `.github/workflows/*`, pillars, policy templates, manifest CLI | All `phenotype-*` repos via `uses: phenotype-ops/.github/workflows/...` |
| `KooshaPari/phenotype-infrakit` | Rust (workspace) | **Infra utilities + tooling** — separate module | Apps that need shared infra helpers |

## Why these are siblings, not merge candidates

The P3 audit script (`tier3-p3-infra-cluster.sh`) listed them as "consolidation candidates" because their names share the `infra` token. That's a **naming collision**, not a domain overlap. Each repo has a different:

- **Primary language** (Rust-compiled-binary vs YAML-vs-justfile-vs-Markdown vs Rust-utility)
- **Primary deliverable** (compiled workspace artifact vs reusable workflows vs utility crate)
- **Consumer audience** (compute apps vs all fleet repos vs apps that import specific utilities)

## Disposition clarification

All three remain canonical in their own scope. No migration is needed.

Future wave: rename one of them to reduce ambiguity
(e.g. `phenotype-infrakit` → `phenotype-infra-utils`).
That is, however, a low-priority cosmetic change.

## Audit

- Original (incorrect) P3 spec: `phenotype-registry/ecosystem-consolidation/dossier/TIER3-P3-INFRA-CLUSTER.md`
- Superseded by this note
- SSOT: `phenotype-registry/registry/disposition-index.json` (PR #541 already reflects reality)
