# DAG + WBS: Cleanup Pass (cliproxyapi-plusplus + thegent)

## Work Breakdown Structure

```
[1] PR Failure Audit
│   └── [1.1] Enumerate cliproxyapi-plusplus open PRs
│   └── [1.2] Enumerate thegent open PRs
│   └── [1.3] Classify each PR by failure cluster
│   └── [1.4] Identify CR-clean PRs
│
[2] CodeRabbit Re-review Wave
│   └── [2.1] Post @coderabbitai full review on CodeRabbit-failing PRs
│   └── [2.2] Monitor CR queue drain
│
[3] Branch Health Audit
│   └── [3.1] Query upstream refs for each open PR head
│   └── [3.2] Compare local branches vs open PR heads
│   └── [3.3] Flag safe prune candidates (none found)
│
[4] Deterministic Action Set (deferred)
│   └── [4.1] Retry wave — after CodeRabbit drains
│   └── [4.2] Cluster wave — after shared CI gates fixed
│   └── [4.3] Hold/serialize thegent infra-failure PRs
│   └── [4.4] Branch-risk guard — no deletion yet
│
[5] Output Artifact
│   └── [5.1] cleanup_matrix.csv with full PR classification
```

## Dependencies

- Step 2 depends on Step 1 completion (must know which PRs are CR-failing).
- Step 3 is independent of Steps 1–2.
- Step 4 is deferred and depends on external conditions (CR drain, CI gate fixes).

## Estimates

| Task | Estimate | Actual |
|------|----------|--------|
| PR Failure Audit | 10 min | ~done |
| CR Re-review Wave | 5 min | ~done |
| Branch Health Audit | 10 min | ~done |
| Deterministic Action Set | TBD | deferred |
