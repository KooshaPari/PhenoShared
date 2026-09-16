# Known Issues

## Deferred Actions (by design)

| ID | Severity | Description | Workaround | Resolution Path |
|----|----------|-------------|------------|----------------|
| KI-1 | **High** | 21 PRs in cliproxyapi-plusplus share same CI failure cluster | Fix shared CI gates first | Cluster wave — deferred |
| KI-2 | **Medium** | thegent infra failures block 4 PRs | Hold until baseline stable | Serialize PR queue |
| KI-3 | **Low** | No safe prune candidates identified | Branch deletion deferred | Revise heuristic later |

## Technical Debt

None introduced during this session.

## Future Work

| ID | Description | Blocked By |
|----|-------------|------------|
| FW-1 | Run retry wave after CodeRabbit rate limit drains | CR queue drain |
| FW-2 | Fix shared CI check manifest in cliproxyapi-plusplus | — |
| FW-3 | Revise branch-risk heuristic to identify safe prune candidates | — |
