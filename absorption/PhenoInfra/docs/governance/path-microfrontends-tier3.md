# Tier 3: Path Microfrontends for `<project>.kooshapari.com`

**Status:** ACCEPTED · 2026-04-25
**Tier:** 3 (path microfrontends within Tier-2 landing)
**Parent governance:** `repos/docs/governance/org-pages-default-pattern.md`
**Sibling architecture:** `phenotype-infra/docs/governance/org-pages-architecture.md`

---

## TL;DR

Every Tier-2 landing site (`<project>.kooshapari.com`) gets four standard
**path-based** microfrontends mounted within the same Vercel project:

| Path             | Purpose                                                                  | Source of truth                              |
| ---------------- | ------------------------------------------------------------------------ | -------------------------------------------- |
| `/docs`          | Build-time render of source repo's `docs/` tree                          | gh API → `repos/<owner>/<repo>/contents/docs`|
| `/otel`          | Embedded OTel UI (Phoenix / Jaeger / Grafana Tempo) iframe               | `PHENO_OTLP_UI_URL` env var                  |
| `/qa`            | Coverage badge + lint status + FR-traceability heatmap                   | repo's `docs/reports/` JSON drops            |
| `/preview/<pr#>` | Vercel PR preview deploys, reachable via stable canonical URL            | Vercel preview alias rewrite                 |

Auth: **none** — all surfaces are public.

---

## Why path-based, not subdomain

The instinct is to mint `docs.<project>.kooshapari.com`, `otel.<project>...`,
etc. We rejected that:

1. **DNS sprawl.** Each subdomain needs a Cloudflare CNAME, a Vercel project,
   and a TLS cert. With ~30 Phenotype repos × 4 surfaces = 120 records to
   manage. Cloudflare's free tier and the Tier-2 bootstrap script already
   strain at ~30 entries.
2. **Cert overhead.** Vercel auto-issues per-host certs. Wildcards aren't
   currently provisioned for `*.kooshapari.com`. Subdomain explosion = 4× cert
   issuance/renewal per project.
3. **Single Vercel project.** Path microfrontends collapse to **one Vercel
   project per Tier-2 landing**, sharing a build, a deploy, and a custom
   domain. PR previews automatically cover all paths.
4. **Cross-surface UX.** Path-based lets `/docs` link to `/qa` with relative
   hrefs and shared nav. Subdomain federation requires CORS / postMessage
   gymnastics.
5. **Bootstrap economy.** The `landing-bootstrap` Rust binary already
   provisions exactly one CNAME, one Vercel project, one repo. Path
   microfrontends require **zero** new infrastructure entries.

**Coexistence with `.dev`:** unchanged from Tier 2 — if `<product>.dev` exists,
`<project>.kooshapari.com` 301-redirects to it (and Tier 3 never builds).

---

## Per-path responsibilities

### `/docs`

- **Renderer:** Astro `[...slug].astro` dynamic route, fetching the source
  repo's `docs/` directory via `repos/<owner>/<repo>/contents/docs?ref=main`
  at build time.
- **Markdown pipeline:** `marked` or `markdown-it` for inline render; for
  larger doc trees, switch to **Astro Starlight** (drop-in) or wire
  **VitePress** as a sub-build mounted at `/docs/`.
- **Caching:** GitHub's API `Last-Modified` headers honored; build re-fetches
  on every Vercel deploy.
- **Graceful degradation:** if the API call fails (rate limit, network,
  missing `docs/`), render a placeholder page that says exactly what failed
  and links to the GitHub source. **Never silent.**

### `/otel`

- **Renderer:** static page with a single full-bleed `<iframe>` pointing at
  `import.meta.env.PHENO_OTLP_UI_URL` (e.g. Phoenix at
  `https://phoenix.phenotype.dev`, or self-hosted Jaeger).
- **Lazy loading:** `loading="lazy"` on the iframe; render an "Open in new
  tab" fallback above the fold for users with strict CSP.
- **Default behavior when unset:** show a clear "Observability backend not
  configured for this project. Set `PHENO_OTLP_UI_URL` in Vercel env vars."
  message. **Do not render an empty iframe.**
- **Auth:** the iframe target may itself require auth; `/otel` does not. We
  inherit whatever the OTLP UI enforces.

### `/qa`

- Three sub-panels, each fed from build-time JSON drops in the source repo:
  - **Coverage** — `docs/reports/coverage.json` (cargo-llvm-cov / pytest-cov)
  - **Lint status** — `docs/reports/lint.json` (clippy + ruff + vale)
  - **FR-traceability heatmap** — `docs/reports/fr-trace.json`
    (FR-id × test-id matrix from `cargo test` annotations)
- **Renderer:** Astro page that imports each JSON via `astro:content` or
  raw `import`, renders cards with progress bars + status badges.
- **When data is missing:** render a card per surface with state "Not yet
  emitted by source repo. Add `docs/reports/<file>.json` to populate." Loud,
  actionable, not silent.

### `/preview/<pr#>`

- Vercel **PR previews are free** and automatic. They deploy at
  `<project>-git-<branch>-<team>.vercel.app`.
- We add a stable rewrite: `/preview/<pr#>` → the Vercel preview alias for
  that PR's branch.
- **Build-time generation:** `getStaticPaths` queries `repos/<owner>/<repo>/
  pulls?state=open` and emits one stub page per PR with an iframe pointing
  at the Vercel alias.
- This is a convenience layer; the Vercel alias remains the canonical URL.

---

## Routing strategy

**Astro file-based routing** is sufficient. No `vercel.json` rewrites needed
for the four standard paths.

```
src/pages/
  index.astro                # / — Tier 2 landing (existing)
  docs/[...slug].astro       # /docs/* — markdown render
  qa/index.astro             # /qa
  otel/index.astro           # /otel
  preview/[pr].astro         # /preview/<pr#>
```

For projects that ship a **VitePress docsite** instead of Astro markdown,
use a `vercel.json` rewrite:

```json
{
  "rewrites": [
    { "source": "/docs/:path*", "destination": "https://<docs-deploy>/:path*" }
  ]
}
```

This delegates `/docs` to a separately-built VitePress bundle while keeping
the rest of the Astro site intact.

---

## Build-time data sources

| Source                      | API call                                                           | Cadence       |
| --------------------------- | ------------------------------------------------------------------ | ------------- |
| Repo metadata               | `repos/<owner>/<repo>` (description, stars, language)              | every build   |
| README                      | `repos/<owner>/<repo>/readme` (HTML accept header)                 | every build   |
| Releases                    | `repos/<owner>/<repo>/releases?per_page=5`                         | every build   |
| `docs/` tree                | `repos/<owner>/<repo>/contents/docs?ref=main`                      | every build   |
| Open PRs                    | `repos/<owner>/<repo>/pulls?state=open&per_page=50`                | every build   |
| Reports (coverage/lint/fr)  | `repos/<owner>/<repo>/contents/docs/reports/<file>.json?ref=main`  | every build   |

`GITHUB_TOKEN` env var is honored in CI for higher rate limits but **not
required**. Anonymous fetches are the supported default; rate-limit failures
trigger graceful-degradation fallbacks.

---

## Lazy loading & code-splitting

- All iframes (`/otel`, `/preview/<pr#>`) use `loading="lazy"` and
  `referrerpolicy="no-referrer-when-downgrade"`.
- `/qa` charts (if any) are loaded as dynamic imports — Astro's island
  architecture means only the panels actually visible ship JS.
- `/docs` pages are statically generated (SSG); no client JS unless the
  source markdown contains MDX islands.

---

## Auth & privacy

- All Tier-3 surfaces are **public**. Phenotype is open-source-first.
- Embedded backends (`PHENO_OTLP_UI_URL`) MAY require their own auth — that
  is opaque to Tier 3.
- No cookies, no analytics scripts beyond what the parent landing already
  has (currently none).

---

## Bootstrap default behavior

`phenotype-infra/iac/landing-bootstrap` scaffolds Tier-3 surfaces **by
default**. Pass `--minimal` to scaffold only the Tier-2 landing.

```
phenotype-landing-bootstrap \
  --slug thegent \
  --repo KooshaPari/thegent \
  # tier 3 included by default
```

```
phenotype-landing-bootstrap --slug foo --repo KooshaPari/foo --minimal
  # tier 2 only
```

The reference implementation lives in `agileplus-landing` and is the source
template the bootstrap copies from.

---

## Failure semantics (Optionality rule)

Per `~/.claude/CLAUDE.md` "Optionality and Failure Behavior":

| Surface | Missing source                            | User-facing behavior                                          |
| ------- | ----------------------------------------- | ------------------------------------------------------------- |
| `/docs` | repo has no `docs/` dir                   | "No docs/ directory in `<repo>`. Add one to populate /docs." |
| `/docs` | gh API rate-limited                       | "GitHub API rate-limited at build time. Retry deploy."        |
| `/otel` | `PHENO_OTLP_UI_URL` unset                 | "Observability backend not configured. Set env var."          |
| `/qa`   | `docs/reports/coverage.json` missing      | "Coverage report not yet emitted. Add the file."              |
| `/preview/<pr#>` | no open PRs                       | "No open PRs. Open one on GitHub to populate."                |

No silent fallbacks. No spinners that never resolve. No empty iframes.

---

## Acceptance criteria

- [x] Reference implementation lives in `KooshaPari/agileplus-landing`.
- [x] Bootstrap scaffolds Tier 3 by default; `--minimal` opt-out exists.
- [x] All four paths return useful content even when data sources are absent.
- [ ] At least one downstream Tier-2 site (e.g. `thegent.kooshapari.com`)
      has been re-bootstrapped to pick up Tier 3.

---

## Related

- `repos/docs/governance/org-pages-default-pattern.md` — Tier 1/2/3 overview
- `phenotype-infra/docs/governance/org-pages-architecture.md` — Vercel + DNS topology
- `phenotype-infra/docs/governance/org-pages-coverage.md` — per-repo deployment status
