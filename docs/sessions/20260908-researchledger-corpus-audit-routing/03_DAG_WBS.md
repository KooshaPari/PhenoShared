# Dependency DAG and WBS

```text
registry routing packet [P]
        |
        +--> ResearchLedger owner evidence/review [G]
        |
        +--> Benchora owner plan/exact-head CI evidence [G]
        |
        +--> cross-project link refresh [G]
```

| Item                                        | Tag | Owner                    | Gate / non-blocker                                                                  |
| ------------------------------------------- | --- | ------------------------ | ----------------------------------------------------------------------------------- |
| Routing packet                              | [P] | registry docs owner      | Complete when protocol documents link owners and evidence limits.                   |
| ResearchLedger corpus implementation        | [G] | ResearchLedger owner     | Blocks ResearchLedger publication only.                                             |
| Benchora #107 plan                          | [G] | Benchora owner           | Requires authorized checkout and owner review; does not block useful registry docs. |
| Benchora scorecard/Sonar/Infisical evidence | [B] | Benchora owner           | Requires exact remote-head evidence; not a ResearchLedger dependency.               |
| Cross-link refresh                          | [G] | registry/owner reviewers | Required before a coordinated release claim.                                        |

No bulk copy, shared branch, or cross-repository merge is authorized.
