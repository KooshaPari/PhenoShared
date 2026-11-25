# rule30-research - absorption provenance

- **Source repo:** KooshaPari/rule30-research
- **Source commit:** `8504e6a6c9a547f5280ae0cecb7500a6cfaf0f12`
- **Source commit subject:** docs(research): docs(research): normalize repository slug in computational lab design spec
- **Repo description:** Recovered local work - salvaged during the 2026-11-08 worktree wrap-up
- **Absorbed on:** 2026-11-11
- **Disposition:** MERGE_SPLIT

## How this repo was split

Private data was separated from code before publication. The public
PhenoShared repo receives code only; anything containing tailnet
addresses, `.ts.net` hostnames, Cloudflare zone identifiers, credentials
or host runbooks goes to the private PhenoRegistry instead.

| Destination | Files |
|---|---|
| `PhenoShared/absorption/rule30-research/` (public) | 6 |
| `PhenoRegistry/repos/rule30-research/` (private) | 0 |

## Selection policy

Absorbed under the infra-whole-repo policy: `host-ops`, `tailnet-smb-setup`
and `harness-ops` are treated as private infrastructure in their entirety,
because a per-file split would still publish host tooling, service names and
runbook cadence. Every other repo was split per file on content.

Verified false positives (canonical test vectors, left as code): W3C
traceparent `4bf92f35...` / `0af76519...`, RFC 4231 HMAC KAT `b0344c61...`,
CGNAT range bounds `100.64.0.0`/`100.64.0.1`, magic DNS `100.100.100.100`,
placeholder token `ghp_abcdefgh...`.

