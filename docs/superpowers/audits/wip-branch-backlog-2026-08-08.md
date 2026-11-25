# Pheno-Harness WIP Branch Backlog (2026-08-08)

Survey of local branches ahead of `main` in pheno-harness, taken from
the post-Round-14 multi-repo backlog.

## Inventory

- **149 total local branches** (up from 35 in the previous audit)
- **99 `wip/2026*` branches** — auto-commit daemon snapshots (noise)
- **35 non-wip branches ahead of main** — 21 stale (already merged
  via other PRs), 14 still actionable

## Categorisation

### Stale (work already merged)

These branches have content already in main via a different PR. Safe
to delete as part of branch cleanup.

| Branch | Ahead | Original PR |
|---|---|---|
| feat/a-plus-t0-install-truth | 1 | #2 |
| feat/eval-assignment-transcript | 1 | #9 |
| feat-eval-assignment-export | 2 | #10 |
| feat/taskspec-meta-pools | 3 | #11 |
| fix-stock-vs-ours-imports | 5 | #12 |
| fix/contract-convert-pythonpath | 7 | #13 |
| fix/cross-repo-audit-rebase | 15 | #16 |
| feat/harbor-verified-pass-wiring | 35 | #29 |
| feat/eval-interchange-ablation-verify | 37 | #30 |
| eval/dual-harness-optimize | 39 | #31 |
| feat/harness-emit-rlvr-fields | 43 | #33 |
| eval/dual-harness-semantic-v2 | 44 | #34 |
| feat/stock-vs-ours-quality-truth | 44 | #35 |
| feat/fixture-forgecode-adapters | 57 | #41 |
| feat/agentora-dual-harness-81 | 58 | #42 |
| feat/agentora-facade-langchain-82 | 60 | #44 |
| feat/dual-harness-v2-matrix | 67 | #45 |
| feat/agentora-facade-ts | 69 | #46 |
| feat/agentora-bench-envelope | 72 | #48 |
| feat/agentora-abi-c-rust | 87 | #49 |
| feat/agentora-abi-zig-mojo | 91 | #50 |
| feat/dual-harness-matrix-report | 96 | #51 |
| feat/agentora-eval-garden-adapter | 98 | #52 |
| chore/preserve-launchd-installer | 121 | #53 |
| feat/agentora-dual-harness-ports | 58 | #43 (closed) |

### Actionable (no PR yet)

These branches have not been PR'd. Should be reviewed for either
opening a PR or closing as obsolete.

| Branch | Ahead | Likely outcome |
|---|---|---|
| feat/bench-vacuous-pass-fix | 3 | small enough to rebase & PR |
| fix/100pct-bug | 4 | small enough to rebase & PR |
| fix/desktop-runtime-mappings | 5 | needs rebase against main |
| fix/desktop-runtime-mappings-canonical | 5 | probably supersedes above |
| fix/pheno-harness-pr54-install | 5 | install-doc fix |
| fix/desktop-launcher-hardening | 8 | needs rebase against main |

### Recovery / dirty-wave

| Branch | Ahead | Note |
|---|---|---|
| recovery/pheno-harness-dirty-20260801 | 2 | snapshot capture |

### Already-merged (zero ahead) — keep as historic

chore/prefer-freethreaded-314, codex/pheno-harness-replay-quality-20260803,
core/intent-graph-v1, feat/agentora-replay-finish,
feat/desktop-live-evidence-20260801, feat/signed-replay-ed25519-20260803,
fix/desktop-evidence-reproducibility-20260805,
fix/pheno-harness-pr54-ci-gates.

## Recommended actions

1. **Open PRs for the 6 actionable branches** (small ahead counts).
2. **Delete the 24 stale branches** that have already been merged
   (work is in main, just the local refs are stale).
3. **Delete the 99 `wip/2026*` branches** (auto-commit daemon noise).
4. **Keep the 8 already-merged historic branches** as reference until
   clean-up of the WIP tree is approved.

## Memory for multi-repo backlog

The 100-PR backlog from Round 14 is across 25 repos:
- sharecli: 38+ PRs
- phenoAI: 23+ PRs
- OmniRoute: 7+ PRs
- thegent: 4+ PRs
- SessionLedger: 4+ PRs
- phenotype-tooling: 3+ PRs
- pheno-harness: 1 PR (#58, merged)
- ... (~20 others, 1 each)

For pheno-harness specifically, the local WIP branch cleanup is the
remaining backlog.
