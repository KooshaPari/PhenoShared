# Public ATS collector (phase 1)

Read-only, standard-library Python 3.10+ discovery service. Does not apply to jobs, contact anyone, or scrape authenticated sites.

## Run

```sh
python collector/collect.py --db jobs.sqlite3
python collector/collect.py --db jobs.sqlite3 --triage-only
python -m unittest discover -s collector -p 'test_*.py' -v
```

The first run seeds an SQLite database. Later runs preserve first-seen timestamps and record `new`, `changed`, or `unchanged` observations. Failed source fetches do not mark old jobs closed.

## Source registry

`sources.json` contains five confirmed public ATS boards. The adapters cover Greenhouse, Lever, and Ashby, but Lever has no confirmed seed board yet. Add further companies only after checking official board slugs.

The `la_review_queue` output is **not** the verified applicant shortlist. It is a broad review queue based on title and LA-area location terms; it does not infer graduation eligibility, 0–2-year experience, work authorization, remote eligibility, or advertised compensation. A dedicated regional classifier is still needed for county boundaries, multi-location roles and remote geography.

## Safety and evidence gates

- Every `active_verified` decision must be supported by an employer-controlled current job page and a recorded check time. The collector never makes that promotion.
- A failed request must not imply closure. A job missing from one successful board fetch needs a follow-up direct check before closure.
- A changed job reverts to `needs_review`, including previously verified jobs.
- Cross-index deduplication and remote-California eligibility remain separate pending components.
- Official salary, graduation band, onsite rules and eligibility need evidence fields before the cockpit can show a job as verified.
- The 30–50 LA and 50–100 all-market targets are throughput goals, never quotas to pad with unsuitable roles.

## Next work packages

1. Add a full employer registry (LA first) and validated geographic buckets.
2. Add GitHub index parsers and official-ATS crosswalks.
3. Add eligibility and compensation evidence tables with per-field provenance.
4. Add direct application-page verification and closure confirmation.
5. Build cockpit candidate views, source health and change alerts.
6. Benchmark coverage, precision, freshness and duplicate rate against an audited gold set.

A six-hour scheduled GitHub Actions workflow is configured to run tests, fetch ATS feeds, persist an SQLite snapshot, and upload a regional review artifact. A successful scheduled ingestion run has not yet been confirmed.

## Existing Cloudflare Worker (canonical operational store)

The pre-existing `jobs-collector/` Worker already writes to the Cloudflare D1 `jobs-db` database. A live read on 2026-10-08 found 23 successful employer boards and a recorded run count of 297 candidates. These are *discovered*, not officially verified, eligible opportunities. The database also contains aggregator observations and location-rank records that must not be treated as qualified LA matches.

The Python SQLite collector is a secondary discovery/audit implementation. **Do not combine its counts with D1 counts** until cross-source identity and reconciliation are implemented. A six-hour GitHub workflow is configured but has not been demonstrated to complete a network ingestion run. The Python workflow's state is not yet synchronized into D1.

Cloudflare Worker source hardening now marks jobs missing from a successful board snapshot `needs_closure_check` rather than `closed`; removes Irvine from the LA location regex; and labels `/candidates` output `unverified`. These changes are in source control and **must be deployed and smoke-tested before treating them as live**. Existing Worker `locRank` still treats remote listings as a separate discovery tier, not evidence of California eligibility. `collector/test_worker_safety.py` documents a remaining expected-failure assertion for that rule.

The live D1 board registry was extended with General Matter and Whatnot (both tier 1). Neither had a completed collection result when added. Do not imply these additions produced verified opportunities until a subsequent run confirms them.

## Live release check (2026-10-08)

The hardened `jobs-collector/index.js` was uploaded via Cloudflare's **content-only** API and confirmed present in the live script. Its D1 `JOBS` and secret `INGEST_TOKEN` bindings remained intact. The D1 database remained readable with 515 stored job records. The live script contains `needs_closure_check`, explicit `verification_status: unverified` response fields, and no longer contains Irvine in its LA regex. Direct public HTTP `/candidates` smoke testing was not possible from the available network, so API response success is **not** claimed. Cloudflare's deployed code and bindings were independently read back.

The live D1 counts include 218 GitHub-index records, 251 `loc_rank=3` observations, 95 records with a parsed 0–2 YOE minimum, and 75 records with a parsed minimum salary; these categories overlap and are not eligibility counts. Remote classification and official eligibility verification remain unimplemented.

## Regional triage (2026-10-09)

`collector/triage.py` exports a regional review queue with explicit `verification_status: unverified`. Its regional buckets separate LA, rest-of-SoCal, Bay Area, Seattle, Portland, Chicago and NYC. Ambiguous remote jobs and unapproved metros remain separate. The output is uploaded as an artifact from the scheduled workflow; it is not yet wired into the Cloudflare D1 database or candidate dashboard. The secondary ATS registry was expanded to 17 public employer boards, using prior live Worker successes as evidence for the additional slugs. The tests include geographic separation and prevent entry-level titles from automatically becoming verified applications.
