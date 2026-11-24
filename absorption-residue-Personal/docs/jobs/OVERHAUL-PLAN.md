# Job-hunter overhaul plan

Draft interpretation, recovered 2026-10-19. This document proposes implementation gates; it does not authorize applications, messages, deployment, or changes to candidate policy.

## Repository and brief recovery

Canonical home: **KooshaPari/job-cockpit**, with this plan in `docs/jobs/`. It contains the application tracker, Worker/D1 collector, secondary Python collector, Jobs frontend, operations contract and traceable job-search asks. GitHub connector owner searches for `job`, `hunter` and `jobs-cockpit` found only job-cockpit. Direct lookups of job-hunter and jobs-cockpit returned 404; those names are unresolved aliases, not proven separate projects. The repository is private; do not mistake that for proof its deployed assets are private.

Recovery baseline: main `7a5e0592da58cca62aaa71b19e4b727a57597b25`. The local checkout was on another branch and its origin/main was older; remote main was inspected independently. No standalone job-search brief exists in main's docs tree. Recover the brief from:

- [Traceable Oct 4–10 ledger, section B](../ledger/asks-tasks-ledger-oct4-10-traceable.md#b-job-search): primary constraints and application review history.
- [Sept 26–Oct 4 ledger, section S2](../ledger/asks-tasks-ledger-sep26-oct4-traceable.md): engineering-first direction and centralized cockpit.
- [Oct 10–11 ledger](../ledger/asks-tasks-ledger-oct10-11-traceable.md): subsequent context and volume expectations.
- [README](../../README.md), [operations](../../OPERATIONS.md), [collector README](../../collector/README.md), [frontend README](../../web/README.md): implemented boundaries and verification requirements.
- [#16](https://github.com/KooshaPari/job-cockpit/issues/16): cross-component provenance, privacy, safety and ownership requirements. This is historical coordination data, not fresh authority.

Recovered intent, pending owner confirmation where policy is ambiguous:

| Area | Recovered interpretation | Source / unresolved point |
| --- | --- | --- |
| Role | SWE primary; product only when it adds engineering experience or meaningful career leverage | Sept ledger S2/S4; do not infer senior eligibility from career aspirations |
| Geography | LA first, historically within 40 miles of the named anchor; hybrid preferred; contract or full time | Oct ledger B1; keep private address out of artifacts; CA-compatible remote requires explicit evidence |
| Experience | 0–2 years primary, 2–4 secondary with explained exceptions | Oct ledger B1; title matching alone is insufficient |
| Compensation | Later recorded floor is $110k base; unknown is flagged, never silently discarded or treated as measured zero | Oct ledger B1; distinguish undisclosed salary from verified fit and from a form's requested numeric answer |
| Targets | Disney Streaming is a core target; recorded employer exclusions/holds need reconciliation | Oct ledger B1/B2 and current employer-policy code differ in coverage; confirm a dated constraint matrix before automating policy |
| Quality / volume | Quality supersedes the earlier ~100 applications/day ambition | Oct ledger B1; collector's 30–50 LA / 50–100 all-market targets are discovery throughput goals, not submission quotas |
| Review / action | Historical asks vary between broad execution and walkthrough-before-send | Oct ledger B2/B5; this overhaul starts read-only, with explicit review and receipts, and grants no submission/outreach authority |
| UX | One cockpit for status, receipts, blockers and owner decisions | Sept ledger S2; automated discovery must work without an active chat |

Verbatim asks remain available in the linked ledgers; this synthesis is visibly draft. Do not treat old ledger assertions about consent, credentials, or completed work as current authorization.

## Recovered current state: what exists and what works

| Component | Evidence of existing behavior | Current limit / confidence |
| --- | --- | --- |
| Application tracker | Root `index.html` / `status.json`; Jobs Astro view preserves status fields; approval controls open drafts | Source inspected. Submission receipts, actual application completion, and browser behavior were not re-audited today |
| Primary discovery | `jobs-collector/`, Cloudflare Worker `job-collector`, D1 `jobs-db`; run recovery and health history tests exist | Live read below proves the health endpoint and a recorded finalized sweep, not every role or deployment binding |
| Secondary discovery | `collector/` Python ATS/index/Whatnot ingestion, SQLite snapshots, regional triage and scheduled Actions | Separate store; do not add counts to D1. Older README caveats and newer operations checkpoints need reconciliation against latest Actions |
| Identity / eligibility | Canonical job/source schema, migrations, verification API and six-field evidence gate already exist | Code presence does not establish trustworthy evidence capture or complete production verification |
| Verification safeguards | `verification.js` requires official activity, location, experience, graduation, authorization and compensation evidence, timestamps and source signatures; 72-hour evidence age bound | Official-host ownership and same-requisition citation binding need adversarial acceptance checks. A plausible HTTPS citation alone is insufficient |
| Operational record | Operations docs record October 12–13 deployment, additive migration and backfill checkpoints | Historical receipts, not a fresh deployment audit. October 8 manual leads are stale today |
| Frontend / packaging | Astro shell and Jobs tests; staged public asset allowlist and source-data preservation described in frontend README | No fresh full build, desktop/mobile QA or privacy export audit claimed by this documentation PR |

**Fresh read-only observation:** `https://job-collector.worker.example.com/health` at `2026-10-19T23:52:58.568Z` returned `health=ok`, latest finalized run `2026-10-19T16:24:06.053Z`, 24 successful / 0 failed boards, age 7.5 hours, `run_identity_scheme=la-day-v1`, and `strict_verified_la=null`. Stored totals were 3,737 records and 1,492 LA-ranked records; **neither is a verified eligible count**. This is a single observation, not proof of sustained health or a complete employer inventory.

Open issue search with label `jobs` returned **zero**. Broader open-issue inspection recovered [#42 live health incident](https://github.com/KooshaPari/job-cockpit/issues/42), [#59 collection-slot identity](https://github.com/KooshaPari/job-cockpit/issues/59), [#16 joint ownership](https://github.com/KooshaPari/job-cockpit/issues/16), and cross-cutting [#95 freshness watch](https://github.com/KooshaPari/job-cockpit/issues/95). The open #42 incident is not automatically closed by today's healthy sample. [#70 cockpit acceptance](https://github.com/KooshaPari/job-cockpit/issues/70) remains relevant for access/freshness. Do not assume the absence of a jobs label means no job work exists.

## Overhaul scope

Build on the existing collectors and cockpit. Deliver one traceable discovery → canonical identity → evidence review → owner decision path. Keep discovery observations, eligible opportunities, prepared applications and confirmed submissions as distinct states.

In scope: dated candidate constraints; source inventory and ownership; cross-source identity; official-page evidence; truthful eligibility and salary unknowns; freshness and closure handling; review queue and decision history; read-only health; reproducible evaluation and rollback receipts.

Later milestones: expand supported ATS/custom sources based on audited coverage gaps; measure sustainable qualified yield; add approved application preparation and resume/writeup review; integrate private correspondence only through separately authorized existing routes.

Excluded from milestone 1: mass applications, submissions, recruiter communications, private mailbox activation, new credentials/connectors, paid infrastructure, unrelated dispensary/economics rewrites, destructive migrations and speculative UI replacement. This PR itself changes documentation only.

## FIRST MILESTONE: trustworthy discovery-to-review slice

Outcome: a reviewer can trace a candidate from a real collection run to one canonical requisition, inspect six current official evidence fields, understand unknown/held states, and see an honest cockpit decision with no external action. **All gates below are pending**; writing this plan does not pass them.

Owners below are proposed accountable roles, not claims of assignment or dispatched agents: Planning = overhaul maintainer; Backend = Worker/D1 maintainer; Verification = evidence/QA maintainer; Frontend = Jobs UI maintainer; Operations = runtime maintainer; Policy = Koosha via Cockpit/Hermes chain. One person may hold multiple roles; record the accepting person and commit before starting a gate. Policy confirmation is routed through the standing chain.

| Gate | Verifiable pass check | Accountable owner | Required evidence |
| --- | --- | --- | --- |
| 1. Baseline and constraints | Publish one dated constraint matrix covering geography, experience, compensation, graduation, authorization, exclusions/holds and action permissions. Every value links to a source; unresolved values stay unknown/held. Reconcile ledger/code differences and record policy confirmation before using disputed values | Planning; Policy confirms disputed policy | Baseline SHA, source map, owner acknowledgments and confirmed/draft field statuses in a single issue/PR tick record |
| 2. Reproducible collector baseline | From a pinned SHA, run `python -m unittest discover -s collector -p 'test_*.py' -v` and `node --experimental-default-type=module --test jobs-collector/test-*.mjs`; zero unexpected failures. Document expected failures and blocked environment dependencies rather than masking them. Capture one finalized collection with explicit source outcomes | Backend | Free GitHub-hosted CI run URLs and complete summaries; collection run ID, timestamp, successful/failed/never-checked source inventory |
| 3. Canonical identity and preservation | Two observations of the same ATS requisition resolve to one canonical identity with both provenances; two distinct requisitions with the same title remain distinct. Repeat ingestion adds no duplicates. Additive migration/re-run preserves legacy records and source history | Backend | Fixture IDs, before/after counts, migration and repeated-ingestion test output, rollback procedure with retained backup/snapshot reference |
| 4. Evidence gate resists false eligibility | Six fields have official employer/ATS URL, exact requisition binding, checked time, excerpt and source signature. Tests reject unrelated job citations, lookalike hosts, unsupported claims, expired/future evidence, missing fields and changed descriptions. Unknown pay is explicitly undisclosed, never $0 or automatic salary-floor success | Verification | Named positive/negative cases and CI logs; redacted evidence rows showing why each state was produced; explicit distinction between verified facts and fit |
| 5. Human-audited evaluation slice | Freeze at least 20 distinct real postings with a recorded selection method across LA, CA-remote, out-of-region, experience mismatch, undisclosed pay and stale/closed cases. Two independent review passes reconcile disagreements. Audit 100% of promoted rows: zero unsupported promotions and zero canonical duplicates; report precision/recall numerators and denominators, including unknowns | Verification | Versioned private-safe gold-set manifest, sampling rule, confusion table, disagreement log and reviewed queue export. If no postings qualify, show zero honestly; a synthetic positive may test mechanics but cannot satisfy a real eligible example |
| 6. Cockpit decision flow and privacy | At desktop and 390px mobile width, trace one real posting from discovery through evidence review to decision/hold. Show source/check time, six field outcomes, freshness, reason, and receipt status. Missing, empty, stale and error states remain distinct. No private research, secrets, personal responses or synthetic test leads enter public exports; review controls cause no send/submit | Frontend | Build/test output (`npm ci`, `npm test` from web), screenshots, keyboard walkthrough, network trace for review actions and public-output allowlist/privacy scan |
| 7. Freshness and recovery | Observe two distinct finalized scheduled runs with age <36h and zero failed boards; separately inject source failure in an isolated fixture and prove it stays degraded without falsely closing jobs. Missing records require closure review; changed evidence returns to review. Preserve `la-day-v1` unless #59's identity migration is explicitly implemented and tested | Operations | Two run IDs and health/Actions artifacts; failure/recovery tests and incident record linked to #42/#59/#95. Same-run polls do not count as two runs |
| 8. Release and handoff | Gate owners sign off 1–7 with evidence at the exact release SHA; any unavailable check remains blocked. If deployment is proposed, validate preview access, bindings, migrations and smoke responses, retain rollback SHA, then follow the existing release route. Publish measured counts and remaining holds in the existing cockpit/PR record | Planning; Operations owns release | One maintained receipt with gate statuses and links, exact SHA, deployment/readback evidence if deployed, rollback rehearsal and current/next owner. No release claim from source presence alone |

Gate 5 is an audit sample, not a statistically proven coverage benchmark. Report observed metrics without extrapolating to all jobs. Throughput targets cannot override any gate. A milestone may conclude that no current role is eligible; it may not substitute unverified counts.

## Ordered task tree and dependencies

```text
0. Recover brief and canonical repo (this documentation package)
   ├─ Source map + current-state distinction
   └─ Proposed owners, gates and unresolved policy
1. Confirm baseline and constraints [G1]
   ├─ Reconcile compensation/exclusions/holds; accept owners
   └─ Freeze baseline SHA and source inventory
2. Establish reproducibility [G2, depends on G1]
   ├─ Offline suites + current CI receipts
   └─ One finalized collection and source outcomes
3. Identity and evidence foundation
   ├─ Canonical/dedup/migration preservation [G3, depends on G2]
   └─ Citation binding + unknown/freshness tests [G4, depends on G1/G2]
4. Evaluate and expose the slice
   ├─ Frozen real-posting audit [G5, depends on G3/G4]
   ├─ Review UI + privacy + accessible mobile flow [G6, depends on G3/G4]
   └─ Two-run health and recovery [G7, depends on G2; coordinate #59]
5. Sign off and hand off [G8, depends on G1–G7]
   └─ Evidence receipt → approved release route → live readback + rollback
6. Subsequent milestones, rescope from measured gaps
   ├─ Coverage and qualified-yield improvements
   └─ Separately authorized preparation/review integrations
```

Rough sequence: planning baseline first; collector reproducibility next; identity and evidence can proceed independently after the baseline; evaluation/UI and the two-run observation window follow. Gate 7 spans actual scheduled executions, so do not promise same-session completion. No staffing or calendar estimate is asserted until owners accept.

## Records and reversibility

Use the existing job coordination issue and the plan PR as evidence entry points; edit the same tick comment as state changes. Use an existing cockpit write route only when available and authorized; do not create credentials or invent completion percentages. Keep gate interpretations draft until confirmed, and preserve the linked verbatim asks.

Safe default here: additive documentation in job-cockpit on `docs/job-hunter-overhaul-plan`, draft PR. Undo by closing the PR without merge; if later merged, revert the plan commit in a new commit. No existing source, data or workflows need deletion.
