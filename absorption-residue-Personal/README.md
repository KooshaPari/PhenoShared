Authored by Instinct.

# Job cockpit

Static page that reads `status.json`. No backend, no secrets. Deploy on Cloudflare Pages (free tier): build command none, output directory `/`.

Update flow: edit `status.json` (a status per application, receipts only for confirmed submissions) and push. Write-ups awaiting approval go in `writeups`; the Approve button opens a prefilled text, it does not send anything by itself.
 Preview deploy: Vercel free tier.


## Job discovery (early implementation)

A read-only ATS discovery collector now lives in [`collector/`](collector/README.md). It stores first-seen/changed observations in local SQLite and produces an LA review queue. It does **not** automatically verify applicant eligibility or update the public dashboard. Run and test instructions are in the collector README. The original application tracker and `status.json` remain unchanged.


## Autonomous job discovery operations

The static application dashboard is separate from the live Cloudflare/D1 collector and the supplemental GitHub Actions ingestion pipeline. For service health, verified-vs-unverified rules, incident recovery, current source exceptions, and reproducible checks, see [OPERATIONS.md](OPERATIONS.md). Neither raw collector counts nor LA-ranked observations are a count of verified eligible jobs.
