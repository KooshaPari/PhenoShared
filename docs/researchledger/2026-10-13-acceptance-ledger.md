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


## October 13 continuation: validated execution and successor forensics

- Hosted research corpus verification [run 38469882345](https://github.com/KooshaPari/PhenoShared/actions/runs/38469882345): **success**; checks all 47 persisted hashes and executes the 70 historical offline research tests. Source validation is not application integration.
- The added `scripts/researchledger/compare_recovery_trees.py` and tests distinguish byte-identical, newer-only, historical-only and changed files. The still-unavailable September 9 object cannot be silently replaced. Exact comparison against that missing source remains **blocked**.
- `.github/workflows/researchledger-youtube-census-manual.yml` is **manual-dispatch only** and references the reviewed `main` checkout. It will need a restricted `YOUTUBE_API_KEY` secret in **PhenoShared**, then a reviewed merge before live collection. No key transfer or completed refresh is claimed.
- [PhenoApps #166](https://github.com/KooshaPari/PhenoApps/pull/166) now includes commit `e322cbc9d8d4e2f28695fad10ea7f03ae0b7874d`: it replaces a non-resolving Trunk Action SHA with actual upstream v1.0.4 commit `22e948f7bb9f870bc6c42625585f1ef27e9c5afc`. Prior Trunk rerun failed during action resolution, before repository linting; the new head's checks must be verified separately.
- A fresh rerun of PhenoApps' former TruffleHog scan [run 35059880205](https://github.com/KooshaPari/PhenoApps/actions/runs/35059880205) concluded **success** on attempt 2. This does not establish passing all current-head security checks.
- [PhenoShared Benchora absorption record](https://github.com/KooshaPari/PhenoShared/blob/main/docs/absorption/Benchora/README.md) names `phenotype-tooling/Benchora/` as an absorbed Rust-crate copy at `f1f9a025`. The current GitHub destination resolves to **private archived** `KooshaPari/zz-zz-agentcheck-PhenoTooling`, and `Benchora/Cargo.toml` was found there. The former standalone Benchora remote is unavailable; this archival copy is not evidence of the finite-state #107 experimental branch or a live benchmark successor.
- RepoLedger old identity remains unavailable. Its current registry catalog row claiming active standalone ownership is a **historical snapshot**, not independently verified current disposition.

### Acceptance impact

The research preservation and test-readiness gate is now independently reproducible on GitHub CI. The later corpus source, application ownership integration, destination secret provisioning and live API run, actual LLM benchmark owner/results, monorepo baseline CI, reviewer acceptance and merges remain open. No proposed artifact should be promoted to a canonical live state merely because this migration ledger exists.


## Read-only local-object recovery helper

The remote lookup for `8822aa14baef2a964288076645edcc493c338688` returned 404 under the old ResearchLedger identity and both inspected destination repositories. This is **not proof of missing local Git objects**. The repository now includes `scripts/researchledger/locate_historical_commit.py`, a bounded network-free locator that checks exact commit-object presence across caller-provided clones, worktree hubs and bare repositories. It never fetches, checks out, writes a branch or changes working-tree files. Invoke it on the desk or backup host with explicit root directories, for example:

```sh
python3 scripts/researchledger/locate_historical_commit.py \\
  --root ~/CodeProjects/Phenotype/repos \\
  --root /Volumes/Backup \\
  --output /tmp/researchledger-git-object-scan.json
```

**No such desk or backup scan was executed in this ChatGPT session**; only hosted negative-control tests are applicable here. A positive exact-commit result would allow a separately reviewed export of the historical tree; a negative result is scoped to the roots inspected and is not evidence of irrecoverability. This output may contain private local filesystem paths, so do not publish its full receipt in public Git without minimization.
