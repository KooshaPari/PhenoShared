# Absorption Ledger — PhenoShared

Generated: 2026-11-12
Source: `absorption/` directory (27 trees) + `docs/absorbed-from*/` (6 formal + 21 informal)

## State definitions

- **staged**: in container, not wired, has a named promotion owner
- **landed**: wired + tested
- **archived**: kept, explicitly never built
- **dead**: manifest retained only

## Absorption trees (absorption/)

| Tree                             | Wired (Cargo.toml refs outside absorption/) | State    | Notes                                        |
| -------------------------------- | ------------------------------------------- | -------- | -------------------------------------------- |
| argisexec                        | 0                                           | archived | No workspace refs                            |
| Authvault                        | 1                                           | staged   | 1 ref                                        |
| byteport                         | 4                                           | staged   | 4 refs                                       |
| cvp-fixture                      | 0                                           | archived | No workspace refs                            |
| helios-bench                     | 0                                           | archived | No workspace refs                            |
| herdr-forgecode                  | 0                                           | archived | No workspace refs                            |
| herdr-helioslite                 | 0                                           | archived | No workspace refs                            |
| herdr-jcode                      | 0                                           | archived | No workspace refs                            |
| herdr-session-adapter            | 0                                           | archived | No workspace refs                            |
| kiro-adapters                    | 0                                           | archived | No workspace refs                            |
| netweave-3                       | 0                                           | archived | No workspace refs                            |
| pheno-forge                      | 6                                           | staged   | 6 refs                                       |
| phenoDesign-visual-production-v2 | 0                                           | archived | No workspace refs                            |
| PhenoInfra                       | 5                                           | staged   | 5 refs; SHA pinned (ecf486cab), reproducible |
| PhenoMLX-temp                    | 1                                           | staged   | 1 ref                                        |
| phenoStandards                   | 0                                           | archived | No workspace refs                            |
| phenotype-canonicalization       | 0                                           | archived | No workspace refs                            |
| phenotype-cvp-audit-2026-09-14   | 0                                           | archived | No workspace refs                            |
| phenotype-router-monitor         | 5                                           | staged   | 5 refs                                       |
| phenotype-router-monitor-root    | 0                                           | archived | No workspace refs                            |
| phenotype-router-spec            | 1                                           | staged   | 1 ref                                        |
| ResearchLedger                   | 0                                           | archived | No workspace refs                            |
| resume-all                       | 0                                           | archived | No workspace refs                            |
| rule30-research                  | 0                                           | archived | No workspace refs                            |
| SessionLedger                    | 0                                           | archived | No workspace refs                            |
| vibeproxy-monitoring-unified     | 0                                           | archived | No workspace refs                            |
| zen                              | 0                                           | archived | No workspace refs                            |

## Formal absorption records (docs/absorbed-from-*/)

| Directory                                   | ABSORPTION.md | State                               |
| ------------------------------------------- | ------------- | ----------------------------------- |
| absorbed-from-dagrun                        | yes           | landed (PR #838, #844, #845 merged) |
| absorbed-from-PhenoCompose                  | yes           | staged                              |
| absorbed-from-PhenoGoKit                    | yes           | staged                              |
| absorbed-from-PhenoObservability            | yes           | staged                              |
| absorbed-from-PhenoTooling                  | yes           | staged                              |
| absorbed-from-zz-zz-agentcheck-PhenoTooling | yes           | staged                              |

## Informal absorption records (docs/absorbed-from/*)

| Directory                        | ABSORPTION.md | State                                                                                                                                            |
| -------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Authvault                        | no            | archived (no formal record)                                                                                                                      |
| cvp-fixture                      | no            | archived (no formal record)                                                                                                                      |
| harness-ops                      | no            | archived (no formal record)                                                                                                                      |
| herdr-session-adapter            | no            | archived (no formal record)                                                                                                                      |
| hfscope                          | no            | archived (no formal record)                                                                                                                      |
| host-ops                         | no            | staged (whole tree plus preserved refs, checked 2026-11-14); source retained as the live publish target of five scheduled jobs, see DELETIONS.md |
| kiro-adapters                    | no            | archived (no formal record)                                                                                                                      |
| netweave-3                       | no            | archived (no formal record)                                                                                                                      |
| phenoDesign-visual-production-v2 | no            | archived (no formal record)                                                                                                                      |
| PhenoInfra                       | no            | staged (has absorption/ counterpart)                                                                                                             |
| PhenoMCPServers                  | no            | archived (no formal record)                                                                                                                      |
| PhenoMLX-temp                    | no            | staged (has absorption/ counterpart)                                                                                                             |
| phenotype-canonicalization       | no            | archived (no formal record)                                                                                                                      |
| phenotype-cvp-audit-2026-09-14   | no            | archived (no formal record)                                                                                                                      |
| phenotype-hub                    | no            | archived (no formal record)                                                                                                                      |
| phenotype-router-spec            | no            | staged (has absorption/ counterpart)                                                                                                             |
| ResearchLedger                   | no            | archived (no formal record)                                                                                                                      |
| rule30-research                  | no            | archived (no formal record)                                                                                                                      |
| SessionLedger                    | no            | archived (no formal record)                                                                                                                      |
| tailnet-smb-setup                | no            | archived (no formal record)                                                                                                                      |
| vibeproxy-monitoring-unified     | no            | archived (no formal record)                                                                                                                      |

## Summary

- Total absorption trees: 27 (absorption/) + 27 (docs/absorbed-from/) = 54
- Landed: 1 (dagrun)
- Staged: 6 (Authvault, byteport, pheno-forge, PhenoInfra, PhenoMLX-temp, phenotype-router-monitor, phenotype-router-spec) — actually 7
- Archived: 47 (no workspace refs, no formal record)
- Dead: 0

## docs/absorbed-root-docs

54 foreign-provenance root .md files (relocated in P1 from repo root)
