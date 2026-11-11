# ResearchLedger - absorption provenance

- **Source repo:** KooshaPari/ResearchLedger
- **Source commit:** `28fe0ccd2573f41aba253a9f8820829ddf7cb727`
- **Source commit subject:** build(deps): bump rustls (#98)
- **Repo description:** Incubating: local-first research ledger and LLM knowledge base
- **Absorbed on:** 2026-11-11
- **Disposition:** MERGE_SPLIT

## How this repo was split

Private data was separated from code before publication. The public
PhenoShared repo receives code only; anything containing tailnet
addresses, `.ts.net` hostnames, Cloudflare zone identifiers, credentials
or host runbooks goes to the private PhenoRegistry instead.

| Destination | Files |
|---|---|
| `PhenoShared/absorption/ResearchLedger/` (public) | 318 |
| `PhenoRegistry/repos/ResearchLedger/` (private) | 0 |

## Files excluded by this repo's .gitignore

6 source files were dropped because PhenoShared's root `.gitignore` matches
them (`*.log`, `worklogs/`, `vendor/`, `audit_scorecard.json`, `*-capture.json`).
None contained credentials. Build logs, vendored third-party Rust crates and
audit scorecards are intentionally not carried into the absorption tree.

## Selection policy

Absorbed under the infra-whole-repo policy: `host-ops`, `tailnet-smb-setup`
and `harness-ops` are treated as private infrastructure in their entirety,
because a per-file split would still publish host tooling, service names and
runbook cadence. Every other repo was split per file on content.

Verified false positives (canonical test vectors, left as code): W3C
traceparent `4bf92f35...` / `0af76519...`, RFC 4231 HMAC KAT `b0344c61...`,
CGNAT range bounds `100.64.0.0`/`100.64.0.1`, magic DNS `100.100.100.100`,
placeholder token `ghp_abcdefgh...`.

