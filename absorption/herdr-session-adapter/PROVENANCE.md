# herdr-session-adapter - absorption provenance

- **Source repo:** KooshaPari/herdr-session-adapter
- **Source commit:** `669e7d82273eededd18adfb9e3ce0959a9a390e2`
- **Source commit subject:** herdr_session adapter A: jcode profile for Paperclip external-adapter lane
- **Repo description:** -
- **Absorbed on:** 2026-11-11
- **Disposition:** MERGE_SPLIT

## How this repo was split

Private data was separated from code before publication. The public
PhenoShared repo receives code only; anything containing tailnet
addresses, `.ts.net` hostnames, Cloudflare zone identifiers, credentials
or host runbooks goes to the private PhenoRegistry instead.

| Destination | Files |
|---|---|
| `PhenoShared/absorption/herdr-session-adapter/` (public) | 12 |
| `PhenoRegistry/repos/herdr-session-adapter/` (private) | 0 |

## Selection policy

Absorbed under the infra-whole-repo policy: `host-ops`, `tailnet-smb-setup`
and `harness-ops` are treated as private infrastructure in their entirety,
because a per-file split would still publish host tooling, service names and
runbook cadence. Every other repo was split per file on content.

Verified false positives (canonical test vectors, left as code): W3C
traceparent `4bf92f35...` / `0af76519...`, RFC 4231 HMAC KAT `b0344c61...`,
CGNAT range bounds `100.64.0.0`/`100.64.0.1`, magic DNS `100.100.100.100`,
placeholder token `ghp_abcdefgh...`.

