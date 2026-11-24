# Research and Ownership

## Boundaries

ResearchLedger owns corpus-repair implementation and its candidate evidence. Benchora owns performance-harness and PR #107 remediation under `BOUNDARY_OWNERS.md` Performance / Benchmark Harness. phenotype-registry owns only routing links.

## Split targets

| Target             | Role                     | Evidence limit                                                                                                                                                                                                                                            |
| ------------------ | ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ResearchLedger     | Sole implementation lane | PR #81 `5ada3d8` is published; `fbf2d0d` and active list-support tests are unpublished/local, not completion evidence.                                                                                                                                    |
| Benchora           | Owner of #107 findings   | The verified hosted plan is pinned at [`65ccb502`](https://github.com/KooshaPari/Benchora/blob/65ccb50288e3ddfa0f537aef80c82c1a26553244/audits/ci-exceptions/2026-09-08-pr107-scorecard-repair-plan.md); prior temporary/unpublished state is historical. |
| phenotype-registry | Link/governance record   | This packet does not replace either owner artifact.                                                                                                                                                                                                       |

## Prior state and deferrals

Historical Benchora #107 `668ceed` reportedly repaired gates green, while the stated snapshot retains scorecard `32/88 < 35`, Sonar fail, and Infisical queued. Exact-head revalidation belongs to Benchora. Historical contradictory catalog records are preserved, not reconciled here.
