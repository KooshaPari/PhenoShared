# ResearchLedger / Emergent Garden acceptance ledger (2026-10-13)

**State:** review-only branch `docs/researchledger-recovery-20261012`, [PhenoShared PR #429](https://github.com/KooshaPari/PhenoShared/pull/429). PhenoShared is the designated research/provenance destination; PhenoApps owns the pending desktop application import. Neither the complete logical product nor fresh data is represented as landed.

## What is verified

| Acceptance unit | State | Evidence |
|---|---|---|
| Historical Wave 5 preservation | **Done on PR branch only** | 47 recovered files exact-match against checksummed fallback, preservation manifest; excluded 25 other archive entries |
| Hosted historical offline source tests | **Pass** | [GitHub Actions run 38469882345](https://github.com/KooshaPari/PhenoShared/actions/runs/38469882345) — all 47 preserved hashes checked; entire 70-test historical corpus suite exercised |
| Recovery importer | **Pass in prior dedicated workflow** | [GitHub Actions run 38326492076](https://github.com/KooshaPari/PhenoShared/actions/runs/38326492076), plus local bundle tests; does not execute an online refresh |
| Latest 2026-09-09 ResearchLedger head | **Unavailable** | Commit `8822aa14baef2a964288076645edcc493c338688` appears in September 9 routing records, but exact object cannot be read via the former repo identity, PhenoShared or PhenoApps |
| Newer tree comparison | **Tool written; live comparison blocked** | `scripts/researchledger/compare_recovery_trees.py`; absent newer source is a hard failure, changed content requires explicit review |
| Destination API acquisition | **Manual workflow written; not run** | `.github/workflows/researchledger-youtube-census-manual.yml` requires destination-scoped `YOUTUBE_API_KEY`, default-branch reviewed source and explicit dispatch. One-day output retention, no raw video/transcript/cookie collection, no permanent Git write |
| Desktop shell | **Import exists, not merged** | [PhenoApps #166](https://github.com/KooshaPari/PhenoApps/pull/166), 316 files at `ResearchLedger/`. Need owner acceptance, up-to-date CI and verified dependency/runtime boundaries |
| Tracker correctness | **Registered CLI; MCP unverified** | [PhenoRegistry #566](https://github.com/KooshaPari/PhenoRegistry/pull/566) corrected the historical `NOT_FOUND` into CLI registration ID3 / `specified`. Historical September 8 PhenoShared copy still has outdated words. Do not duplicate the feature |
| Benchora/RepoLedger successor | **Unresolved** | Old GitHub names and stable identities inaccessible; a previously described finite-state pilot cannot stand in for live LLM agent evaluation |
| Fleet-wide CI | **Not green** | Root monorepo workflows still fail on unrelated docs, action pins, workflow parse/lint, and other baseline issues. Distinguish from passing specific research verification workflows |
| Merge/release | **Not done** | PR429 remains draft, no default-branch or product release changes |

## Completion blocks

1. Locate exact latest research source from a retained clone, exported worktree, mirror, bundle or accessible Git object. Do not infer deletion merely from 404. Compare against historical Wave 5 using the supplied read-only tool and preserve all differences.
2. Agree PhenoShared ingestion/domain paths and PhenoApps desktop shell ownership; verify app build/test and restore essential routing links without reviving a duplicate ResearchLedger product.
3. Enable the destination-scoped restricted YouTube Data API v3 key **only in the approved secret store**, then manually run the reviewed collector. Former repository secrets are not assumed to migrate. A failed or partial API enumeration cannot silently become a successful Atom snapshot.
4. Store refreshed provider data privately or in short-lived artifacts consistent with the [YouTube API Services Developer Policies](https://developers.google.com/youtube/terms/developer-policies); do not promote expired September metadata from the archive.
5. Reconcile the old benchmark/reference source and locate current owner. Run and report actual model/agent comparison only after frozen task corpus, budgets, actuator/evaluator revisions and safety floor.
6. Fix *actual blocking* relevant CI failures by owner, obtain reviews, merge gated PRs, and only then mark registry and AgilePlus completed.

## Bounded closure rule

A missing exact transcript is an explicit source-availability gap, not a license to invent text. A partial or one-off public comment sample is not exhaustive historical coverage. The direct-paper selected-methods reviews and synthetic evaluation checks are research evidence, not reproduced claims of creator systems or agent-topology superiority.

## Historical state / no duplicate authority

`docs/sessions/20260908-researchledger-corpus-audit-routing/` remains an earlier session record, **not current status**. The current project card `projects/ResearchLedger.json` refers to an older standalone decision and needs owner-reviewed reconciliation, not an unreviewed destructive rewrite. This ledger supersedes those historical statements *for migration tracking only*; ResearchLedger's canonical claims and private-vault authority remain separate from the fleet catalog.
