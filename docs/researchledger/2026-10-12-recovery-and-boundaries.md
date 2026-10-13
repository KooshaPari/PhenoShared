# ResearchLedger / Emergent Garden recovery — 2026-10-12

**State: recovery staging; not merged, not a completed ResearchLedger absorption.**

Owner-designation input: ResearchLedger research and shared ingestion/provenance should be integrated into **PhenoShared**; the desktop/UI package is separately proposed in **PhenoApps #166**. Do not silently equate this operational plan with an accepted product architecture or an existing running service.

## Evidence checked

| Evidence | Observed disposition |
|---|---|
| Former `KooshaPari/ResearchLedger` repository, stable ID `1308558334` | Not accessible through the current GitHub connector (404); **not** proof of deletion or historical source absence |
| Latest **referenced** old research commit | `8822aa14baef2a964288076645edcc493c338688` in the September 9 routing record; no current Git-object readback |
| Verified fallback archive | Wave 5, SHA-256 `5197f26bd5ba82abffd2d03354174352f5cf06efee1ea99f33e201d589aa99c3`, 72 checksummed payloads; **older than the referenced September 9 work** |
| Curated fallback staging | 47 Markdown, YAML and Python files from that archive, totaling 506,406 bytes; 25 other entries excluded |
| PhenoApps #166 | Open, unmerged, 316-file application import at `ResearchLedger/` targeting `apps-extract`; does not establish inclusion of the Emergent Garden corpus |
| Tracera #1028 | Merged documentation; does not establish runtime implementation |
| Agentora #212 | Merged documentation; later repository archived/quarantined |
| PhenoRegistry #566 | Merged; established CLI registration ID 3 / `researchledger-corpus-audit-routing`; live MCP governance remains separate |
| AgilePlus #1073 | Open/stale earlier work item; no blanket closure warranted |
| Former Benchora / RepoLedger | Prior names/IDs unavailable to the connector; track as unresolved successors, not deleted facts |

## Canonical components proposed for review

* PhenoShared: shared source/claim/provenance engine, collection tooling, and **permissioned, refreshed** research derivatives. Keep the ResearchLedger logical product and source authority singular.
* PhenoApps: desktop frontend/application shell if #166's imported code and dependencies pass its owner review. Do not merge #166 just because it is mergeable.
* Research private vault: source text, raw comments, access credentials and other material not suitable for a public repository. Do not publish private contents into PhenoShared.
* Tracera: graph trace/evidence projections for the persistent product model; not a second research corpus.
* AgilePlus: work/spec execution authority. PhenoRegistry: cross-repo routing. Benchora successor: experimental comparators.

## Recovery and publication protocol

1. **Recover latest first.** Find an actual accessible object for `8822aa14...` and any later commits/backup/worktree. Verify paths, hashes, and adoption state against the imported application and historical bundles. Until a source object is recovered, classify it `REFERENCED_UNAVAILABLE`.
2. **Verify fallback bytes.** Run `python -m unittest discover -s tests/researchledger -v` then `python scripts/researchledger/recover_wave5.py --archive /path/to/emergent-garden-wave5-verified-handoff.zip --destination /tmp/rl-stage`. The command fails on hash or manifest mismatch, path traversal/symlink, content collision, or potential credential.
3. **Stage but do not publish stale API Data.** Only curated historical narrative and source tooling are staged. YouTube Data API metadata, descriptions, comments and snapshots from September 5 are past the stated October 5 refresh-or-delete deadline; do not reintroduce those entries as live current data.
4. **Avoid clobbering.** Compare every staged path against a recovered newer source before copying. Conflict means manual three-way reconciliation with source revisions, not overwrite.
5. **Rebuild live acquisition under destination credentials** only after reviewing current allowed scopes, quota, retention, rate budgets and privacy boundaries. Secrets from the old repository are not assumed to migrate.
6. **Run actual quality gates** for independent engine, UI shell, ingestion adapters and file bridge. A passing fixture test is not application CI or live source completeness.
7. **Re-run the benchmark successor** with actual agent treatments and fairness controls. The finite-state reference is a separate test; it cannot be used to rank LLM coordination topologies.
8. **Only then** update registry/AgilePlus and one-way fleet projections. Require a reviewed merge per destination and an evidence-based release decision.

## Critical policy gate

Google's [YouTube API Services Developer Policies](https://developers.google.com/youtube/terms/developer-policies), section III.E.4, require other stored non-authorized API Data to be refreshed or deleted within 30 days. Historical snapshots can be cited accurately for chronology, but do not import expired stored descriptions or comment datasets as active data. Different categories of statistics and authorized data may have additional rules.

## Stop conditions

No secret in Git, no public-comment full-text mirror, no invented Git lineage, no raw source execution, no automatic ownership transfer, no fabricated test pass, and no merge/release based solely on the prior assistant's assertions. Missing pieces must remain `UNVERIFIED` or `BLOCKED`.

## Links to existing evidence

* [PhenoApps #166](https://github.com/KooshaPari/PhenoApps/pull/166)
* [AgilePlus #1073](https://github.com/KooshaPari/AgilePlus/issues/1073)
* [PhenoRegistry #566](https://github.com/KooshaPari/PhenoRegistry/pull/566)
* [Tracera #1028](https://github.com/KooshaPari/Tracera/pull/1028)
* Current PhenoShared routing source: `docs/sessions/20260908-researchledger-corpus-audit-routing/`; treat its September 8 status as historical.
* Source catalog `projects/ResearchLedger.json` still says standalone KEEP, so it must **not** be silently assumed to reflect the new authority split.

This document is a **migration acceptance packet**, not an asserted completed migration.
