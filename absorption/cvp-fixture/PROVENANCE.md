# cvp-fixture - absorption provenance

- **Source repo:** KooshaPari/cvp-fixture
- **Source commit:** `b00c7abdeb52a1d74a5b26bce16c131e2e43014c`
- **Source commit subject:** docs(audit): add substrate-family absorb audit log and bridge export
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
| `PhenoShared/absorption/cvp-fixture/` (public) | 17 |
| `PhenoRegistry/repos/cvp-fixture/` (private) | 0 |

## Selection policy

Absorbed under the infra-whole-repo policy: `host-ops`, `tailnet-smb-setup`
and `harness-ops` are treated as private infrastructure in their entirety,
because a per-file split would still publish host tooling, service names and
runbook cadence. Every other repo was split per file on content.

Verified false positives (canonical test vectors, left as code): W3C
traceparent `4bf92f35...` / `0af76519...`, RFC 4231 HMAC KAT `b0344c61...`,
CGNAT range bounds `100.64.0.0`/`100.64.0.1`, magic DNS `100.100.100.100`,
placeholder token `ghp_abcdefgh...`.

