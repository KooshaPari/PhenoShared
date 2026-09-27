# ADR 0007 — Runner Label Routing

- **Status:** Proposed (stub)
- **Date:** 2026-04-24

## Context (outline)

- Jobs have different resource profiles: lightweight (lint, fmt, docs), medium (test, small build), heavy (cargo release, VRAM).
- Need deterministic routing from job definition → runner node.

## Decision (outline)

Label taxonomy:

- `[self-hosted, oci, light]` — OCI primary/secondary for small jobs
- `[self-hosted, oci, medium]` — OCI secondary, GCP e2-micro
- `[self-hosted, heavy, home]` — home Mac for cargo release, GPU jobs
- `[self-hosted, burst, hetzner]` — Phase-2 spillover

Routing algorithm: job author declares `runs-on: [self-hosted, heavy, home]`; Woodpecker dispatches to any agent matching all labels.

## Consequences (outline)

- Clear mental model; predictable routing.
- Requires agent-side label declaration at registration.

## Alternatives (outline)

- Resource-request matcher (CPU/RAM) — rejected: Woodpecker doesn't support; over-engineered.
- Single runner pool — rejected: heavy jobs would starve light ones.

## Related

- ADR 0003 (home heavy), ADR 0005 (Woodpecker), `docs/specs/runner-routing-spec.md`

> **TODO:** Finalize label list, document default fallback behavior.
