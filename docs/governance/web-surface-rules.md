# Web surface rules: domains, gating, deploy targets

Status: adopted 2026-10-17 from the owner's directives. Applies to every new and existing service.

## Default

Everything is internal software. Default is internal-only. Nothing is public unless it is static docs or a landing page.

## Domain taxonomy

| Domain | Purpose | Exposure |
| --- | --- | --- |
| phenotype.space | Org level. `<project>.phenotype.space` = project landing page and docs | Public static only. No apps, APIs or backends |
| pheno.studio | Deploy studio: apps, backends, dashboards, APIs | Gated |
| pheno.shop | Payment portals | Gated, high sensitivity |
| kooshapari.com | Personal pages. Personal infra tools stay gated | Pages public, tools gated |

## Gate stack (free tiers)

1. Static docs and landing: public on GitHub Pages, Cloudflare Pages or Vercel. No private data, no tokens in the bundle.
2. Apps on Vercel or Cloudflare: Cloudflare Access in front (proxied record, owner-only policy). WorkOS login is added as the Access OIDC identity provider when that integration is verified, so one login satisfies both. Vercel Authentication is a second lock on previews.
3. Desk backends: bound to the tailnet only (Tailscale Serve), no public listener. A Vercel app reaches them server-side with a verified Vercel OIDC token, through a Cloudflare Tunnel protected by an Access service token.
4. Wildcard Access apps cover `*.pheno.studio` and `*.pheno.shop` so a new hostname is gated by default. Specific apps override the wildcard.

## Rules

- A new hostname on pheno.studio or pheno.shop needs no extra step to be gated. A hostname on phenotype.space is public, so only static docs or landing may be served there.
- Apps found on phenotype.space move to pheno.studio.
- Dead DNS records (origin errors 522 or 525) are removed after owner approval. Do not delete without it.
- Check HTTP status before and after any gating change and keep the receipt in the PR.
- Static IP allowlisting is not used (paid on Vercel).

## Deploy defaults per project

Every repo carries a landing page and a docs site at minimum, built from the shared template and deployed to one of GitHub Pages, Cloudflare Pages or Vercel (free tier). Competitor notes live in `docs/compete/` and are part of the docs site.
