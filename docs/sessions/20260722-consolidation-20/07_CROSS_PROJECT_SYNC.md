# Cross-Project Sync

## Disposition Matrix

| Disposition | Repositories | Sync requirement |
|---|---|---|
| ARCHIVED-PRESERVED / complete | `zz-archive-AgilePlus-recovery-20260714` (docketed as `AgilePlus-recovery-20260714`) | Preflight, rename, archive, and postverification complete; preserved, never deleted |
| HOLD | `AgilePlus-recovery-evidence-20260714` | Preserve as unique evidence; never delete |
| HOLD | `phenotype-registry-archive`, `phenotype-org-audits-archive2`, `PhenoRuntime-archive`, `ResilienceKit-archive`, `phenotype-shared-archive` | Preserve pending parity evidence |
| HOLD | `Stashly`, `phenotype-teamcomm` | Resolve contradictions |
| VERIFY-ONLY | `agileplus-spec-harmonizer-tool-archive-2026-07-14`, `4sgm-archive`, `Parpoura-archive`, `phenoResearchEngine-archive`, `home-recovery-2026-07-archive`, `phenotype-monorepo-state-archive`, `agent-user-status-archive` | Capture branch, SHA, and content proof |
| VERIFY-ONLY | `Quillr` | Confirm tombstone evidence |
| VERIFY-ONLY | `router-docs` | Private non-fork; confirm complete absorption into OmniRoute |
| VERIFY-ONLY | `template-commons` | Private non-fork; confirm complete absorption into phenokits |
| HOLD | `PriceyApp` | Leave fork remote untouched |

## Coordination Contract

- Registry is the disposition ledger; source repositories remain preservation evidence.
- Lane T owns consolidation evidence; the preservation sublane enforces non-destructive handling.
- Exactly one READY action completed: `AgilePlus-recovery-20260714` is now
  `zz-archive-AgilePlus-recovery-20260714`, `ARCHIVED-PRESERVED`. Its sole head
  `recovery/isolated-20260714` is exact commit `0aafdf9692c11abb6e426f36857aeec7bb6cd942`, and
  canonical AgilePlus contains that exact commit and tree
  `eb82ced16353219d85aa83c925819ae48cb36c16` with the exact head.
- Postverification records `archived=true`, `private=true`, `fork=false`, default branch
  `recovery/isolated-20260714`, one branch, zero tags, unchanged
  `pushed_at=2026-07-16T00:20:23Z`, and an old-name redirect. No deletion occurred.
- The other 19 repositories retain their HOLD or VERIFY-ONLY dispositions.
- No other project receives a READY remote-mutation signal until both SHA and content parity are
  recorded.
- Cross-project updates must carry the actual default branch and corrected Batch A destination.

## Tranche 2 Sync

| Candidate | Parent | State |
|---|---|---|
| harmonizer tool archive | AgilePlus | PARITY-PROVEN / POLICY-HOLD |
| `4sgm-archive` | QuadSGM | HOLD: four refs absent |
| `Parpoura-archive` | Parpoura / phenodocs | HOLD: three refs absent |
| `phenoResearchEngine-archive` | phenoResearchEngine / pheno | HOLD: exact ref absent |
| `home-recovery-2026-07-archive` | unresolved | HOLD: parent proof absent |
| `phenotype-monorepo-state-archive` | phenotype-registry | HOLD: four unique commits absent |

## Tranche 3 Sync

| Candidate | Parent | State |
|---|---|---|
| `phenotype-registry-archive` | phenotype-registry | HOLD: incomplete 23-head namespace, nine objects absent |
| `phenotype-org-audits-archive2` | phenotype-registry | PARITY-PROVEN / POLICY-HOLD: 7/7 exact |
| `PhenoRuntime-archive` | unresolved: PhenoRuntime / pheno / legacy collection | HOLD: 2/3 absent plus boundary conflict |
| `ResilienceKit-archive` | split: ResilienceKit / Python SDK / future Rust SDK | HOLD: 6/7 absent plus ownership split |
| `phenotype-shared-archive` | phenotype-shared | HOLD: 2/2 absent |
| `agent-user-status-archive` | phenotype-tooling | HOLD: 7/7 absent |

## Tranche 4 Sync

| Candidate | Boundary | State |
|---|---|---|
| `AgilePlus-recovery-evidence-20260714` | private forensic evidence | KEEP-STANDALONE |
| `PriceyApp` | upstream fork | KEEP-FORK / UNTOUCHED |
| `Quillr` | split pheno + phenodocs claims | HOLD: 25-ref map absent |
| `Stashly` | canonical cache product | KEEP-STANDALONE |
| `router-docs` | OmniRoute | HOLD: source commit/tree absent |
| `template-commons` | phenokits-commons | HOLD: five unique commit/tree pairs absent |
| `phenotype-teamcomm` | protected coordination primitive | KEEP-STANDALONE |

First-20 disposition totals: one `ARCHIVED-PRESERVED`, two `PARITY-PROVEN / POLICY-HOLD`, three
`KEEP-STANDALONE`, one `KEEP-FORK / UNTOUCHED`, and thirteen evidence or boundary HOLD entries.
