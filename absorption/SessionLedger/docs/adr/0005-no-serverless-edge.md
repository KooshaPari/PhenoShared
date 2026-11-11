# ADR 0005: No serverless / edge deploy target

- Status: Accepted
- Date: 2026-07-14
- Decision owners: SessionLedger maintainers
- Related: `docs/adr/0001-desktop-companion-scope.md`, `docs/ops/distribution.md`, audit-v38 C11 L114

## Context

SessionLedger ships as a **local daemon** (`sl-daemon`) plus a **desktop / web
viewer** (`sl-viewer`). Distribution channels today are GitHub Releases,
homebrew/winget manifests, OCI images for self-hosted traditional servers, and
systemd + reverse-proxy samples.

Audit-v38 C11 L114 asks for a serverless / edge deploy surface (Cloudflare
Workers, Vercel, Netlify edge functions, and similar). SessionLedger’s data
plane watches local session files, writes OKF artifacts to a host directory, and
serves a loopback HTTP API — none of which map cleanly onto a request-scoped
edge isolate without inventing a remote sync product.

## Decision

SessionLedger **does not** target Cloudflare Workers, Vercel, Netlify Edge, AWS
Lambda@Edge, or other serverless/edge runtimes for `sl-daemon` or `sl-viewer`.

Deploy surfaces that **are** in scope remain:

1. Native desktop installers / portable archives
2. Traditional server (systemd, process-compose, OCI on a VM/host)
3. Local loopback HTTP for the viewer ↔ daemon contract

Absence of `wrangler.toml`, `vercel.json`, or Workers/Pages project files is
**intentional**, not an unfinished gap.

## Consequences

- Packaging and ops docs list GitHub Releases + traditional-server paths only.
- L114 evidence is this ADR + `docs/ops/distribution.md` cross-link (N/A with
  explicit decision), not a Workers scaffold.
- Revisit only when a product phase adds remote multi-tenant hosting with a
  clear edge-fronted API and stored state outside the operator’s machine.

## Revisit triggers

| Trigger                                             | Why                                            |
| --------------------------------------------------- | ---------------------------------------------- |
| Multi-tenant hosted SessionLedger is in charter     | Edge/CDN fronting becomes relevant             |
| Daemon data plane moves off host filesystem watches | Edge isolates could host API edges             |
| Explicit customer requirement for Workers/Vercel    | Record a superseding ADR before adding configs |
