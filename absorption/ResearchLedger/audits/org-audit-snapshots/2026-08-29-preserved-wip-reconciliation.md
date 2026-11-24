# Snapshot: Preserved WIP Reconciliation — 2026-08-29

**Date:** 2026-08-29 UTC

**Scope:** `KooshaPari/ResearchLedger` local worktrees and `origin` refs
**Disposition:** preserve all recovery refs; no bulk merge, delete, force-push, or history rewrite.

## Summary

This reconciliation reviewed the non-ancestral ResearchLedger refs before
starting new feature work. The normal development lines have already passed
through review and merge. The remaining `wip/preserve-*` refs are Airlock
recovery evidence, not an integration queue. Most identified functional
surfaces are represented by current `main` code and regression coverage. The
four initially unique patches received isolated file-level comparison after
this snapshot. No preserved patch warrants a recovery merge; one product gap
is recorded separately as a modern, token-safe GitHub onboarding task.

## Evidence collected

| Check                                       | Result                                                                                              |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `main`                                      | `04837035ad344bb2abd1ff8de7ed86a884067b90`; clean and aligned with `origin/main` at collection time |
| Open pull requests before this audit branch | None                                                                                                |
| Historical pull request records             | 70, fetched before PR #72 was created                                                               |
| Non-ancestral `origin` refs                 | 85                                                                                                  |
| Ordinary/dependency/CI refs                 | 13; each maps to an already merged or closed PR                                                     |
| Preserved Airlock WIP refs                  | 72 refs, 64 distinct Git trees                                                                      |
| WIP commit subjects                         | 39 explicit snapshot/preserve, 8 governance/docs/dependency, 25 semantic candidates                 |

The inventory was produced without ref mutation using:

```zsh
git for-each-ref refs/remotes/origin --no-merged=origin/main
git log origin/main --format='%H%x09%s'
gh api --paginate 'repos/KooshaPari/ResearchLedger/pulls?state=all&per_page=100' \
  --jq '.[] | [.number, .state, .merged_at, .head.sha] | @tsv'
```

The paginated PR query returned 70 historical records at collection time. PR #72
is intentionally excluded from that count because it was created to review this
reconciliation record after the snapshot.

## Ordinary ref disposition

| Area                          | Evidence                   | Disposition |
| ----------------------------- | -------------------------- | ----------- |
| TypeScript native config      | PR #69                     | Merged      |
| Parallel vault test isolation | PRs #70 and #71            | Merged      |
| Mergify commit formatting     | PR #68                     | Merged      |
| CodeQL/scorecard repair       | PRs #58 and #62            | Merged      |
| Dependency updates            | PRs #63, #64, #65, and #66 | Merged      |
| Earlier Mergify repairs       | PRs #47, #51, and #55      | Merged      |

## Semantic WIP reconciliation

| Preserved intent                                  | Current-main evidence                                                                         | Disposition               |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------- | ------------------------- |
| TS7/native typecheck                              | PR #1                                                                                         | Integrated                |
| Reddit and X provider ingest/capture              | PR #3 and current `reddit.rs`, `x.rs`, `provider_html.rs`                                     | Integrated                |
| Chunking, hybrid retrieval, and reranking         | PR #4 and current `chunking.rs`, `rag.rs`, `embeddings.rs` tests                              | Integrated                |
| Resource verification, CSP, and provider UI hooks | current `verify_resources.mjs`, `verify_csp.mjs`, and `App.tsx`                               | Integrated                |
| Release workflow and signing hardening            | PR #15, PR #40, and the notarized 0.1.0 macOS artifact                                        | Integrated                |
| Provenance/audit model                            | PR #36 and current `audits/` structure                                                        | Integrated                |
| Unicode ranking normalization                     | `rag::tests::reranker_normalizes_unicode_case_and_character_length`                           | Integrated                |
| Embedding compatibility filtering                 | PR #48 and `storage::tests::vector_search_excludes_incompatible_model_version_and_dimensions` | Integrated                |
| Bounded consented reference traversal             | PR #49 and `storage` traversal/lease tests                                                    | Integrated                |
| Mergify modernization                             | PRs #41, #51, #55, and #68                                                                    | Integrated                |
| `c019316` embedding and GitHub delta              | Embeddings/RAG is integrated and hardened; historic device-code onboarding was removed        | Retain; no recovery merge |
| `021209e` consented reference-queue delta         | Current queue command, tests, bounded traversal, consent recheck, and leases are stronger     | Integrated/superseded     |
| `9d01799` A+ integration snapshot                 | 39 conflict-marker lines; all represented paths/commands exist in current main                | Non-integrable evidence   |
| `3520179` resolved A+ integration snapshot        | Resolved sibling; all represented paths/commands exist with hardened replacements             | Integrated/superseded     |

### Completed isolated comparisons

`c019316d5c2b` adds embeddings/RAG behavior that current `main` retains with
stricter loopback, proxy, redirect, and test-only-constructor controls. Its
only absent behavior is the historic GitHub device-code client. That client
was introduced by `2c6b1a8` and removed in `378228c`; current import instead
uses an already-authenticated local `gh` session. This is not a safe
cherry-pick candidate. If first-run GitHub connection remains required, it
must be designed as a new, least-privilege onboarding flow that never exposes
tokens to the webview or application UI.

`021209ec2e14` is present in evolved form: current `queue_reference_fetch`
validates the source/link relationship and now benefits from the bounded crawl,
durable run state, consent recheck, and leased-claim behavior. `9d0179920058`
is deliberately non-integrable raw conflict evidence. Its resolved sibling,
`35201796f0ff`, has no missing functional path, and all represented Tauri
commands are registered in current `main`; its historic helpers were replaced
by stronger current
implementations.

## Preservation decision

The `origin/wip/preserve-20260822-researchledger/unreachable-*` refs remain
protected evidence. A snapshot name, a divergent ancestry graph, or an older
file-level diff is not proof of a recoverable feature; importing any such
snapshot wholesale would regress newer merged work and invalidate provenance.

A future recovery proposal must identify one narrow behavioral delta absent
from `main`, include a focused test, and enter review as a fresh PR. The
comparison queue is now empty: all reviewed semantic lines are integrated,
superseded, governance-only, or preserved non-integrable evidence. The refs
remain untouched as provenance. The separate GitHub onboarding product task is
new work, not recovery work.

## Supersedes

None.
