# DAG and WBS

```text
W0 manifest
  -> W1 namespaced preservation imports
       -> W2 GitHub reachability proof
            -> W3 archive proposal (separate HITL gate)
```

| Lane | State | Exit condition |
|---|---|---|
| W0 manifest | complete | Valid 20-row ledger committed and pushed |
| W1 import | pending | Missing refs exist in canonical parents |
| W2 proof | pending | GitHub resolves every imported SHA/ref |
| Local-gap audit | pending | Empty remote names reconciled with local storage |
| W3 archive | blocked | Requires W2 evidence and sponsor approval |

## Cockpit source-boundary lane

```text
C0 snapshot hash evidence
  -> C1 immutable preservation record
       -> C2 atomic writer and renderer migration
            -> C3 explicit source-boundary repository decision
                 -> C4 AgilePlus operational cutover
                      -> C5 Tracera consumer adoption
```

| Lane | State | Exit condition |
|---|---|---|
| C0 snapshot hash evidence | complete | 06:53 source, renderer, and output hashes recorded |
| C1 preservation record | complete | Non-Git chain and later rehash drift recorded additively |
| C2 atomic migration | blocked | One atomic writer and reproducible renderer exist |
| C3 source-boundary decision | blocked | Sponsor-approved repository boundary and preservation plan |
| C4 AgilePlus cutover | blocked | C2 and C3 complete; operational writes use AgilePlus |
| C5 Tracera consumption | blocked | C4 exposes a stable, governed read contract |
