# Cross-Project Sync

| Parent | Sources |
|---|---|
| AgilePlus | AgilePlus recovery, recovery evidence, harmonizer provenance |
| Tracera | Five empty recovery shells pending local reconciliation |
| OmniRoute | Superroot shell, monorepo archive, Rust workspace hold |
| phenotype-omlx | `temp` hold and one missing `tmp/main` ref |
| phenotype-registry | Audit evidence archives and this ledger |
| thegent | PR2 recovery; share CLI dedupe hold |
| substrate | thegent-dispatch provenance |
| PhenoPlugins | phenoVessel parity hold |
| governance owners | phenoStandards split between templates and workflows |

Merge order is W0 registry ledger, W1 parent refs, W2 proof, then a separately approved archive wave.

## Cockpit migration roles

| System | Role | Current gate |
|---|---|---|
| AgilePlus | Operational successor for workflow writes and lifecycle | Blocked on atomic writer/renderer migration and source-boundary decision |
| phenotype-registry | Schema, governance, and preservation SSOT | This additive evidence record is committed here |
| Tracera | Future governed read-model consumer | Blocked on a stable AgilePlus-produced read contract |
| Local `phenotype-dag/`, `beads/`, `cockpit/` | Preserved historical source chain | Non-Git; do not initialize, move, delete, or replace |

No cross-project source replacement, repository creation, or consumer repoint is authorized by
this preservation packet.
