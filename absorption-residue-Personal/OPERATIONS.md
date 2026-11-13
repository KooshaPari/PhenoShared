# Job Cockpit — operations and verification gates

This project has two different data flows. Do not merge their counts or call either output an eligible-job list without independent verification.

## Production architecture

- **Application dashboard:** static `index.html` + `status.json`. Application receipts must represent confirmed submissions only.
- **Primary collection database:** Cloudflare Worker `job-collector`, D1 `jobs-db`. Published public API:
  - `https://job-collector.worker.example.com/health`: run freshness, board success/failures, stored-observation counts. `strict_verified_la=null` is intentional while field-level verification is unavailable.
  - `https://job-collector.worker.example.com/review`: discovery/review observations capped at 200, **not** verified eligibility. It may include duplicate, senior, stale, or ineligible jobs; it is not an application shortlist.
  - `/candidates`: similarly unverified public job records.
- **Supplemental collection:** `collector/` runs on GitHub Actions and stores a separate SQLite snapshot plus official Whatnot careers catalog, using no application credentials. The two stores are **not synchronized**, and their counts cannot be added together.
- **Tests and autonomous operations:**
  - `job-collector-tests.yml`: offline regression tests.
  - `job-collector-scheduled.yml`: every six hours; fetch public ATS boards, export regional unverified review, fetch Whatnot's official careers catalog, validate output, and publish a monotonic snapshot. Concurrent GitHub pushes are retried without force-push, and a newer remote snapshot wins.
  - `job-health-monitor.yml`: every six hours; test live HTTP JSON contracts, freshness and source failures. Opens/reopens one incident under the finalized-run policy; recovery resets the streak and leaves closure to owner review.
  - `whatnot-source-probe.yml`: tests official Whatnot custom HTML parser (Python) and JS parsing of fetched public markup, *not* Worker outbound network access.

## Operational checks

1. Read `/health` and confirm `health=ok`, age under 36h, zero failing boards, and expected source coverage.
2. Check `/review` contract: `kind=unverified_la_review_queue`; never call the returned count qualified jobs. The result can be truncated.
3. Check GitHub's latest `Public ATS discovery` run; regression tests, ATS fetch, Whatnot fetch, JSON validation, SQLite integrity, guarded publication and artifact upload must all pass.
4. Check `Job collector live health`: collection status stays degraded for any failed board; incident opening follows the finalized-run policy below. Issue #42 is the existing incident. An absent opening condition never closes it automatically.
5. Check the scheduled GitHub snapshot against `collector/data/whatnot.json`. Its official career links require separately checking the actual role posting, graduation band, salary, work arrangement and experience requirements.

The monitor opens/reopens the existing titled incident after two distinct consecutive degraded **finalized** runs, failed boards strictly above 10% of checked boards in the latest finalized run, or a latest finalized run older than 36 hours. The denominator is `boards_ok + boards_failed` from that same run, independent of current board inventory. Exactly 1/10 or 2/20 does not qualify by percentage; 1/9 does. Recovery resets the run streak; issue closure remains an owner decision. A first low-failure run still fails the strict health check and Actions job.

The 36-hour threshold is retained from both the established Worker `/health` contract and `collector/probe_live.py`. It allows the existing daily collector interval plus 12 hours for completion/recovery; the six-hour monitor cadence can delay detection until the next probe. Raw `finished_at` timestamps determine incident staleness, avoiding rounded-age boundary errors. `/health` now computes its existing age/status from the latest finalized row, while retaining `latest_run` for attempt diagnostics. Error-only rows (`boards_ok IS NULL`) cannot make a stale completed run fresh. The two newest finalized rows carry stable `la-day-v1:<day>` IDs; deployment versions and repeated polls do not create runs. The separate am/pm slot proposal (#59) must introduce an explicit identity migration if implemented.

Each monitor artifact contains a small checkpoint (two run summaries, completion clock, first observation, conflicting IDs). The next main monitor run restores the newest available artifact from this same workflow, including failed checks; concurrency serializes monitors. Artifact/API/parse failures stop incident writes rather than reset the clock. Expired/deleted evidence, or prior monitor runs without any recoverable report, requires operator restoration. A true first monitor run can bootstrap; existing legacy reports migrate their observation time. The existing retention is 21 days. During Worker rollout the old single-row contract supports adjacent-day evidence only; a polling gap cannot prove consecutive failures. Missing or malformed rows stay unknown and break a streak. Zero checked boards is degraded, with an undefined percentage: two distinct explicit `no active boards` finalizations or staleness can qualify. With no trusted completion at all, persistent absence qualifies after 36 hours from the first recorded observation; no completion timestamp or success count is invented. Conflicting outcomes for one ID are quarantined, and a timestamp revision cannot refresh that ID's clock.

## Whatnot failure / fallback

The former Whatnot Ashby public posting API returned 404. On October 12, the primary Worker recovered using an official Ashby hosted-page fallback; the D1 daily run recorded 25/25 successful boards and 19 Whatnot postings. Do not assume this fallback will stay healthy without checking the live `/health` endpoint. Do not treat a failed board as a company closure.

Whatnot's official public careers catalog at `https://www.whatnot.com/careers/discover` is readable by the **Python GitHub Actions** fetch path. The validated Oct. 11/12 capture contained 151 distinct job URLs, 40 engineering-related titles and 20 with LA among listed work locations; **none of those counts imply 0–2-year applicant eligibility**. `collector/data/whatnot.json` records these source observations.

Node's direct GitHub Actions fetch of the same catalog received HTTP 403. The experimental `whatnot-careers` adapter in the Worker code is **NOT SEEDED OR DEPLOYED**; its parser was cross-tested against official HTML, but that does not prove outbound Worker access. Never deploy it as a required board without a lawful live fetch success.

## Promotion into an eligible application lead

A posting can be counted toward the 30–50 local target only when:
- Official employer posting and application link are current and opening remains active.
- The requisition is deduplicated by employer/ATS ID and canonical official URL.
- Los Angeles work location or explicit California-compatible remote eligibility is established.
- Experience band and graduation criteria fit the candidate; explicit sector/work authorization restrictions remain separate gates.
- Advertised base compensation is recorded, or marked undisclosed (never inferred from an index).
- Each field has source URL, check time and confidence; a substantive description change requires reverification.

Only then label `active_verified`. Automated index presence, an HTTP 200, and a low YOE parser number are **not** proof of eligibility. Known manual corrections cannot be treated as evergreen.

## Safety boundaries

Read-only discovery. Never apply, message, follow, connect, write LinkedIn DMs, or alter personal recruiting correspondence automatically. No background assistant session is needed for the GitHub/Cloudflare schedules.

## October 12–13 verification release checkpoint

- PR #50 merged on main (commit `360e45ed`). The complete five-module Worker was deployed to production, and live HTTP tests confirmed public `/health` and `/review` and an unauthorized HTTP 401 from private `/verified`.
- An isolated D1 preview database, `job-cockpit-verification-preview`, was created; schema migration `jobs-collector/migrations/0002-verification.sql` passed there twice. The same additive migration then succeeded in production `jobs-db`. Existing legacy source records remained intact.
- Production `canonical_job` and `canonical_source` were backfilled from direct official ATS observations only, using `0003-backfill-ats.sql` (initially held in PR #51). This resulted in 327 distinct direct-board requisitions, including 198 coarsely LA-ranked records. `job_verification` contained zero completed employer-evidence records. These are **not** 198 qualified opportunities.
- Stage Worker smoke tests passed and the preview workers.dev subdomain was subsequently disabled. The preview D1 contains synthetic test records; never count those as live candidate evidence.
- After merge, supplementary Whatnot catalog sync discovered three overseas roles without parsed locations; their raw source records are retained and the sync validator now skips them rather than blocking the entire catalog. GitHub Actions' `JOB_COCKPIT_INGEST_TOKEN` was empty in the observed run, so it is not yet sending supplemental source records.
- A follow-on PR #51 adds automatic canonical/source upserts to the *existing* Cloudflare board scans, so the core system no longer relies on copying the GitHub catalog or provisioning an extra secret. Its deployment, CI and live scheduled ingestion are separate acceptance checks; don't report them complete based on the data backfill alone.
- The first unattended post-merge GitHub Actions discovery run failed at the catalog sync validation step; its fix was committed, but subsequent new runs must independently pass before declaring full unattended GitHub ingestion recovered.

Data model distinction: `job` remains the legacy discovery table, `canonical_job` is a normalized posting identity, `canonical_source` tracks where it was observed, and `job_verification` requires six fresh, official employer-page evidence checks. No user-authorized applications or recruiter communications occur in these pipelines.
