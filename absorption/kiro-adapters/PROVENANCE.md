# kiro-adapters - absorption provenance

- **Source repo:** KooshaPari/kiro-adapters
- **Source commit:** `a18cb9f4cfa68149bd3822ae41bc60cd54e38dc3`
- **Source commit subject:** feat(ops): read-only check that reports unconfined desk execution
- **Repo description:** Harness adapters: drive Kiro Crew (kirocrew) and the Kiro coding CLI (kirocode) from jcode or any MCP client. Zero-dependency MCP stdio server, 10 tools, JSON result envelope.
- **Absorbed on:** 2026-11-11
- **Disposition:** MERGE_SPLIT

## How this repo was split

Private data was separated from code before publication. The public
PhenoShared repo receives code only; anything containing tailnet
addresses, `.ts.net` hostnames, Cloudflare zone identifiers, credentials
or host runbooks goes to the private PhenoRegistry instead.

| Destination | Files |
|---|---|
| `PhenoShared/absorption/kiro-adapters/` (public) | 160 |
| `PhenoRegistry/repos/kiro-adapters/` (private) | 1 |

## Files withheld to the private registry

- `acceptance/windows-sandbox-posture.md`

## Selection policy

Absorbed under the infra-whole-repo policy: `host-ops`, `tailnet-smb-setup`
and `harness-ops` are treated as private infrastructure in their entirety,
because a per-file split would still publish host tooling, service names and
runbook cadence. Every other repo was split per file on content.

Verified false positives (canonical test vectors, left as code): W3C
traceparent `4bf92f35...` / `0af76519...`, RFC 4231 HMAC KAT `b0344c61...`,
CGNAT range bounds `100.64.0.0`/`100.64.0.1`, magic DNS `100.100.100.100`,
placeholder token `ghp_abcdefgh...`.

