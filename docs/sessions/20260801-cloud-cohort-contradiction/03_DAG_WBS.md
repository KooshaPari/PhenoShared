# DAG and Work Breakdown

```text
current GitHub metadata snapshot
          |
          v
classify 11 archive-named target/archived / 2 in-place / 3 unavailable / 4 active
          |
          +--> preserve heads and local evidence
          |
          +--> obtain actor + timestamp + sponsor receipt
                         |
                         v
             reconcile session docs and registry (approval required)
                         |
                         v
                    resume CI-gated promotion
```

| Work package | Status | Exit condition |
|---|---|---|
| C1 API snapshot | complete | Twenty rows and full default-branch SHAs recorded |
| C2 contradiction classification | complete | 11/2/3/4 classes independently counted |
| C3 provenance preservation | pending | Bundles or immutable refs for every unresolved row |
| C4 authorization receipt | blocked pending evidence | Actor/time and sponsor receipt for archive/rename changes |
| C5 registry reconciliation | blocked by C4 | Sponsor-approved row update, separately reviewed |
| C6 CI promotion continuation | deferred | Resume after C4/C5 and registry CI repairs |
