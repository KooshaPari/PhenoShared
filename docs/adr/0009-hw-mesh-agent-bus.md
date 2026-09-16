# ADR 0009 — HW Mesh Agent Bus (Phase 2)

- **Status:** Proposed (stub, Phase 2)
- **Date:** 2026-04-24

## Context (outline)

- Agents on different nodes need to coordinate (e.g., a planner on oci-primary spawns a heavy-build task on home-mac).
- Current approach: queue jobs via Woodpecker; no agent-to-agent RPC.
- Desired: direct, authenticated RPC over Tailscale for low-latency coordination.

## Decision (outline)

Build `hw-mesh-agent-bus` crate:

- Rust; `tonic` gRPC over Tailscale MagicDNS.
- mTLS via Tailscale node identity.
- Typed protos for `PlanRequest`, `BuildDispatch`, `HealthPing`, `ResultSink`.
- Publish as a workspace crate in a dedicated repo (TBD: `phenotype-hw-mesh`).

## Consequences (outline)

- Low-latency coordination; avoids polling Forgejo for state.
- Adds a new crate to maintain.

## Alternatives (outline)

- NATS — rejected: adds a broker; yet another service to run.
- HTTP + JSON — rejected: typed protos preferred.
- Zenoh — promising; revisit if gRPC proves heavy.

## Related

- ADR 0004 (Tailscale), ADR 0007 (label routing), `docs/runbooks/day3-hw-mesh.md`

> **TODO:** Spec proto schema, pick port range, define auth model.
