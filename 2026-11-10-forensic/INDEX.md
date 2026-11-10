# PhenoShared — Forensic Inventory Index

Repo: `KooshaPari/PhenoShared` · checkout `~/CodeProjects/Phenotype/repos/PhenoShared`
Commit basis: `origin/main` @ `6ec4ae563` (1,214 commits on main) · working tree observed at `ad667428b` on `layer/governance-happy-path-claims`
Analysed: 2026-11-10 · read-only static inspection, no builds, no CI runs
Note on drift: the working tree was being modified by another process during the analysis (`crates/phenotype-dag-core` staged for deletion, root `Cargo.toml` edited). Structural counts held; the 283-member figure is point-in-time and was 282 at the last check.

## Deliverables (read these)

| File | Lines | What it answers |
|---|---|---|
| `DELIVERABLE-1-codebase-atlas.md` | 321 | What is in the repo, how it is laid out, where the code mass actually is |
| `DELIVERABLE-2-qa-matrix.md` | 150 | Which quality controls exist, which ones are actually enforced, what is unproven |
| `DELIVERABLE-3-product-dossier.md` | 260 | What the product is, who it is for, how it got here, what it risks |
| `REMEDIATION-PLAN.md` | 230 | What it would take to reach the intended shape, a **decentralized container SDK**: per-crate publication class × layer, the seam contract (`cargo package` as the consumability test), a multi-ecosystem publication matrix, phases, and the four classification calls |

## Evidence lanes (source material behind the deliverables)

| File | Lines | Covers |
|---|---|---|
| `A-git-history-forensics.md` | 333 | Full history 2026-02-23 → 2026-11-09 (259 days): commit cadence, authors, branch topology, tags, velocity curve |
| `B-codebase-atlas.md` | 374 | Raw structure: tiered crate families, per-crate Rust LOC, non-Rust surfaces |
| `C-qa-matrix.md` | 143 | Raw control inventory across 92 workflows |
| `D-product-dossier.md` | 523 | Long-form dossier source: positioning, capabilities, contract record |
| `E-branch-inventory.md` | 284 | All 74 remote branches classified, stale-vs-live, ahead/behind |
| `F-absorption-archaeology.md` | 263 | Which other products were absorbed into this repo, when, and whether they are still reachable |
| `G-runtime-surface.md` | 264 | Ports, binaries, daemons, protocols, storage engines the code exposes |
| `H-supply-chain.md` | 324 | 1,904 lockfile packages, vendored trees, license posture, dependency concentration |
| `I-docs-corpus.md` | 277 | The 10,532-markdown documentation corpus: what is authoritative vs stale |
| `J-ecosystem-position.md` | 136 | Where PhenoShared sits among the sibling repos |
| `V-verification.md` | 276 | Independent re-measurement of the headline numbers |
| `VERIFY-structure.md` | 61 | Structural audit of the assembled deliverables (fence parity, table columns, duplicate headings) |
| `AUDIT-final.md` | 49 | Independent cross-document consistency audit: line counts, headline numbers, seam vocabulary |
| `parts/prov-focus.md` | 46 | Direct measurement of `crates/focus-*` and `crates/connector-*`: 43 + 9 crates, 43,601 Rust LOC, 7 `[[bin]]`, single-commit provenance, zero core inbound edges |
| `parts/prov-sharecli.md` | 36 | Direct measurement of `crates/sharecli*` and the `absorption/` trees: 12 crates / 119,855 LOC with no upstream on disk; `absorption/PhenoTooling` does not exist |

## Method

Twelve lanes in parallel (A–J plus V-verification), each bounded, each writing its own file before
finishing. The three deliverables were then assembled from section files under `parts/` rather than
synthesized in one pass, so that a failed route could not lose the whole document. `parts/` is the
disassembly of the deliverables and is retained so any single section can be corrected and the
deliverable deterministically rebuilt:

```bash
cat parts/atlas-*.md  > DELIVERABLE-1-codebase-atlas.md
cat parts/qa-*.md     > DELIVERABLE-2-qa-matrix.md
cat parts/dossier-*.md > DELIVERABLE-3-product-dossier.md
```

## Reading discipline

Anything marked **UNKNOWN** was not measurable from the read evidence. It is not zero, and it is not
an estimate. In the QA matrix, `PASS` means a control was observed wired into a workflow that runs on
push/PR — not that a run was observed blocking a merge. No CI run was executed anywhere in this analysis.
