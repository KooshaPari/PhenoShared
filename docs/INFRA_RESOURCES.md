# Org infrastructure resources ($0 tier)

Authored by Instinct, Koosha's pilot assistant. Pending Koosha's review.

This repo is public. Nothing here is a secret, an account ID, a resource ID or a token. Secrets live in Infisical and are referenced by name only.

Limits below were read from each vendor's own docs or pricing page on 2026-10-07. Free tiers change, so treat the linked page as the source of truth and re-check before depending on a number.

## What the org already has

This doc adds to existing material. It does not replace it.

| Area | Where it lives |
| --- | --- |
| Reusable CI workflows (CI, CodeQL, security scan, trufflehog, secret-guard, terraform-plan, release) | `.github/workflows/`, usage in `.github/README.md` |
| Composite actions | `.github/actions/` |
| Repo hygiene files | `.github/CODEOWNERS`, `PULL_REQUEST_TEMPLATE.md`, `ISSUE_TEMPLATE/`, `dependabot.yml`, `release-drafter.yml`, `codecov.yml` |
| Governance and branch protection policy | `.github/GOVERNANCE.md`, `.github/BRANCH_PROTECTION_SPECS_MAIN.md` |
| Per-language repo templates | `crates/hexa-kit/templates/` |
| Secrets manager client (Infisical) | `crates/fabric-daemon/src/auth/secrets.rs` |
| Compute and IaC consolidation (nanovms, PhenoCompose, BytePort) | `KooshaPari/PhenoInfra` repo (GitHub description: Compute/Infra consolidation monorepo), absorption notes in `absorption/PhenoInfra/` |
| Org index and repo roles | `KooshaPari/PhenoRegistry` (`ECOSYSTEM_MAP.md`) |
| Cron and local ops runbook | `docs/CRON_OPS.md` |
| Cost attribution template (empty) | `docs/COST.md` |

Not covered anywhere yet, and the reason for this doc: a single inventory of the hosted free-tier services, and a bootstrap recipe for a new repo that uses them.

`docs/INFRASTRUCTURE.md` is the pheno-harness container/Kubernetes guide, not an org-level doc.

## 1. Free-tier stack

### Cloudflare (one account, Workers Free plan)

| Service | Free limits | Use for |
| --- | --- | --- |
| Workers | 100,000 requests/day, 10 ms CPU per invocation, 50 subrequests per invocation, 100 Workers, 5 cron triggers per account | Collectors, thin JSON APIs, webhooks. Chunk long jobs across cron fires. |
| Cron Triggers | 5 per account, 10 ms CPU each | Scheduled collection. Pick a fixed morning window and reuse it. |
| D1 (serverless SQLite) | 10 databases, 500 MB each, 5 GB total, 5M rows read/day, 100k rows written/day, 50 queries per invocation, 7-day Time Travel | Default structured store. One database per product. Write with `db.batch()`. |
| Workers KV | 1 GB, 100k reads/day, 1,000 writes/day, 1,000 list/day, 1 write per second per key | Small config and cache. Not a database: the write cap is low. |
| R2 | 10 GB-month storage, 1M Class A and 10M Class B operations/month, no egress fee | Files, exports, backups. |
| Queues | 10,000 operations/day (a delivered message is about 3 operations) | Fan-out and retries. Rarely needed at this scale. |
| Workers AI | 10,000 Neurons/day | Embeddings (bge models) and small LLMs (Llama 3.2 1B/3B class). Large models burn the daily allocation fast. |
| Pages | 500 builds/month, 1 concurrent build, 100 custom domains | Static sites and Pages Functions that read D1/KV. |
| Zero Trust / Access | Free plan (check the seat cap in the dashboard; not re-verified here) | Put private apps behind email one-time-PIN or SSO. |
| Email Routing and Email Workers | Routing is free; 30 domains per zone | Inbound aliases and programmatic inbound mail. |

Sources: https://developers.cloudflare.com/workers/platform/limits/ , https://developers.cloudflare.com/d1/platform/limits/ , https://developers.cloudflare.com/d1/platform/pricing/ , https://developers.cloudflare.com/kv/platform/pricing/ , https://developers.cloudflare.com/r2/pricing/ , https://developers.cloudflare.com/queues/platform/pricing/ , https://developers.cloudflare.com/workers-ai/platform/pricing/ , https://developers.cloudflare.com/pages/platform/limits/ , https://developers.cloudflare.com/email-routing/limits/ , https://developers.cloudflare.com/cloudflare-one/account-limits/

Account-wide caps are shared by every product: D1 rows, Worker requests and Workers AI Neurons are per account, not per Worker. Budget across products.

### Outside Cloudflare

| Service | Free limits | Use for |
| --- | --- | --- |
| Neon (Postgres) | Up to 100 projects; each project gets 100 CU-hours/month, 1 GB storage, scale to zero | When a product needs real Postgres features. |
| Turso (libSQL/SQLite) | 100 databases, 5 GB storage, 500M rows read and 10M rows written/month (as listed on the pricing page) | SQLite you need outside Cloudflare. |
| Sentry | Free Developer plan, 1 user. Event quota not confirmed here, check the plan page | Error tracking for apps. |
| Uptime monitoring | UptimeRobot Free: 10 monitors | Pings for public endpoints. |
| Infisical | Free plan: unlimited projects, 5 identities, secret references and imports | Secrets. See below. |

Sources: https://neon.com/pricing , https://turso.tech/pricing , https://sentry.io/pricing/ , https://uptimerobot.com/pricing/ , https://infisical.com/pricing

## 2. New-repo bootstrap

Do these once at org level. After that a new repo is a template plus a few names.

### Cloudflare account layout
- One Cloudflare account for personal and hobby products. Everything is namespaced by product name, not by account.
- Naming: Worker `<product>-collector` or `<product>-api`; D1 `<product>-db`; KV namespace `<product>`; Pages project `<product>`.
- Resource IDs (D1 and KV) are not secret but are account-specific. Keep them in the repo's `wrangler.toml` only when the repo is private. In a public repo, inject them at deploy time.
- Deploy through Workers Builds from GitHub, with the root directory set to the Worker's folder and the Worker name matching `name` in `wrangler.toml`.

### D1 per product
- One D1 database per product (about 10 allowed). Do not share a database across unrelated products.
- Schema lives in `schema.sql` next to the Worker. The Worker may bootstrap it on first run with `CREATE TABLE IF NOT EXISTS`.
- Plan around the daily caps: 100k rows written/day account-wide. Batch writes and upsert rather than append where possible.
- Public read path: Pages Function or Worker returns JSON from D1. Keep the response shape stable when migrating from KV.

### Access app pattern
- Anything with private data goes behind a Cloudflare Access application: one application per hostname, policy allowing the owner's email addresses, one-time PIN as the identity provider.
- After creating it, check that an anonymous request is redirected to sign-in, and that the OTP flow works.
- Public status endpoints must carry public data only.

### Cron
- Run all daily collectors in one morning window so alerts land in the morning. Cron times are UTC, so recompute when daylight saving changes.
- 10 ms CPU per invocation means long jobs run as many small fires, each doing a bounded amount of work with state kept in D1 or KV.

### Infisical (reference only)
- Convention: one Infisical project per product, environments `dev`, `staging`, `prod`, secrets named in UPPER_SNAKE_CASE, shared org values in a separate `org-shared` project and pulled in with secret references.
- Repos read secrets from Infisical at deploy or runtime (see `crates/fabric-daemon/src/auth/secrets.rs` for the Rust client) and from GitHub Actions secrets for CI. Secret values never go in the repo, in issues, in PRs or in docs.
- The reusable `trufflehog.yml` and `secret-guard.yml` workflows should be enabled on every repo.

### GitHub defaults for a new repo
- Start from the closest template in `crates/hexa-kit/templates/` or copy `.github/` essentials: `CODEOWNERS`, `PULL_REQUEST_TEMPLATE.md`, `ISSUE_TEMPLATE/`, `dependabot.yml`.
- Call reusable workflows from this repo rather than copying them: `uses: KooshaPari/PhenoShared/.github/workflows/ci.yml@main`.
- Branch protection on `main`: require a pull request, at least one approval, dismiss stale reviews, require the CI check. Follow `.github/GOVERNANCE.md`.
- Add the repo to `PhenoRegistry` so the ecosystem map stays accurate.
- Default branch name `main`. Private by default; make public only when the repo holds nothing private.

### Checklist
1. Create repo from template, set branch protection.
2. Create Infisical project and environments.
3. Create D1 database, Worker and (if needed) Pages project with the naming above.
4. Put private UIs behind Access and verify anonymous access is blocked.
5. Add the uptime monitor and Sentry project if the product is user-facing.
6. Register in PhenoRegistry.

## Open items for the owner
- Confirm the Infisical project and environment names above match what already exists, since this doc only proposes a convention.
- Confirm the Zero Trust seat cap and the Sentry event quota from the dashboards; neither was verifiable from public pages.
- `docs/COST.md` is still an empty template. Free-tier usage per product could be tracked there.
