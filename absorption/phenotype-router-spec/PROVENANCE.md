# phenotype-router-spec - absorption provenance

- **Source repo:** KooshaPari/phenotype-router-spec
- **Source commit:** `5b043a1f4b73a5f639dc1288d873b0a17b427736`
- **Source commit subject:** fix(p3): remediate top audit findings (#1)
- **Repo description:** Protocol spec for the phenotype router A2A surface. JSON schema for RouterDispatch, RouterMailbox, RouterTrace, RouterArtifact. Markdown protocol docs. Reference implementation pointers to substrate::{engine-agentapi, omniroute-adapter, cliproxy-adapter}.
- **Absorbed on:** 2026-11-11
- **Disposition:** MERGE_SPLIT

## How this repo was split

Private data was separated from code before publication. The public
PhenoShared repo receives code only; anything containing tailnet
addresses, `.ts.net` hostnames, Cloudflare zone identifiers, credentials
or host runbooks goes to the private PhenoRegistry instead.

| Destination | Files |
|---|---|
| `PhenoShared/absorption/phenotype-router-spec/` (public) | 22 |
| `PhenoRegistry/repos/phenotype-router-spec/` (private) | 0 |

## Selection policy

Absorbed under the infra-whole-repo policy: `host-ops`, `tailnet-smb-setup`
and `harness-ops` are treated as private infrastructure in their entirety,
because a per-file split would still publish host tooling, service names and
runbook cadence. Every other repo was split per file on content.

Verified false positives (canonical test vectors, left as code): W3C
traceparent `4bf92f35...` / `0af76519...`, RFC 4231 HMAC KAT `b0344c61...`,
CGNAT range bounds `100.64.0.0`/`100.64.0.1`, magic DNS `100.100.100.100`,
placeholder token `ghp_abcdefgh...`.

