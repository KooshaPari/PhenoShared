# Implementation Strategy

Use link-not-copy routing. ResearchLedger changes stay in ResearchLedger. Benchora findings stay in the hosted Benchora artifact [`audits/ci-exceptions/2026-09-08-pr107-scorecard-repair-plan.md`](https://github.com/KooshaPari/Benchora/blob/65ccb50288e3ddfa0f537aef80c82c1a26553244/audits/ci-exceptions/2026-09-08-pr107-scorecard-repair-plan.md), pinned at `65ccb502`. The registry stores this packet and links only.

Do not mutate `domain-roles.json`, `disposition-index.json`, absorption records, schemas, or owner-repo sources. The Benchora artifact is already committed and hosted; no future registry refresh is needed for its link.
