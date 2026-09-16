# ADR 0006 — Vaultwarden as Canonical Credential Store

- **Status:** Proposed (stub)
- **Date:** 2026-04-24

## Context (outline)

- Credentials currently scattered across `.env`, 1Password, browser keychains.
- Need: single canonical store with rotation policy, agent read-access, human write-access.

## Decision (outline)

- Self-host Vaultwarden on `oci-primary` behind Cloudflare Tunnel.
- Bitwarden CLI on all nodes for runtime credential fetch.
- Rotation policy: 90 days for API tokens; 180 days for SSH keys; immediate on compromise.

## Consequences (outline)

- Single point of failure — mitigated by nightly encrypted backup to R2 (Phase 2).
- Agent workflows need `bw` CLI and a service account with scoped read access.

## Alternatives (outline)

- 1Password team — rejected: paid.
- HashiCorp Vault — rejected: operational overhead disproportionate to scale.
- SOPS + age + Git — rejected: no web UI, human UX suffers.

## Related

- `docs/governance/security-policy.md`, `docs/specs/credential-inventory.md`

> **TODO:** Flesh out threat model, backup procedure, agent auth flow.
