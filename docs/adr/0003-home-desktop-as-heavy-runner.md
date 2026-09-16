# ADR 0003 — Home Desktop as Heavy Runner

- **Status:** Accepted
- **Date:** 2026-04-24

## Context

Cargo `--release` workspace builds for the Phenotype monorepo run 5–10× faster on the user's home Mac (M-series, 64 GiB RAM, NVMe) than on OCI Ampere. VRAM-bound ML experiments and `xtask`-heavy jobs are impractical on free-tier cloud. The Mac is online most of the day but is also used for Parsec gaming sessions, which demand full GPU + CPU priority.

## Decision

Attach the home Mac to the Tailscale tailnet as node `home-mac` and register it as a **Woodpecker agent** with labels `[self-hosted, heavy, home]`. Routing rules (ADR 0007) send `cargo build --release`, VRAM jobs, and manual heavy dispatch to this label. The agent is managed by a **launchd plist** that:

1. Starts the Woodpecker agent at login.
2. Watches for Parsec process presence; if `Parsec.app` is foregrounded, the agent is **paused** (see ADR 0008 for pause semantics).
3. Resumes when Parsec exits.

The home Mac is NEVER exposed to the public internet; all ingress is Tailscale-only.

## Consequences

**Positive**

- ~5–10× speedup on heavy Rust builds.
- Zero marginal cost (hardware already owned).
- Full access to 64 GiB RAM and local NVMe for `target/` caching.
- GPU available for ML experiments when idle.

**Negative**

- Availability is not 24/7 (gaming, reboots, travel).
- Requires local launchd management; cannot be Terraform-provisioned.
- Broader attack surface on the user's personal machine — mitigated by Tailscale ACLs and running the agent as a limited user.

## Alternatives considered

1. **Dedicated home mini-PC** — rejected: new spend, adds physical hardware to manage.
2. **Cloud GPU spot instances** — rejected: cost is not zero; cold-start latency ruins iteration speed.
3. **Run heavy jobs on OCI Ampere** — rejected: 4 OCPU is insufficient for `cargo build --release` on the monorepo within reasonable wall-clock.

## Related

- ADR 0007 (runner labels), ADR 0008 (Parsec pause), `docs/runbooks/day1-home-runner-setup.md`
