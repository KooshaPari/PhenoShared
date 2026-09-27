# ADR 0001 — Hybrid Compute Mesh (7 nodes)

- **Status:** Accepted
- **Date:** 2026-04-24
- **Deciders:** Koosha Pari (solo-dev), scaffold agent

## Context

The Phenotype org has an active agent swarm (up to 50 concurrent subagents) plus heavy Rust cargo builds, VRAM-bound ML experiments, and ongoing CI across 30+ repos. GitHub Actions billing is exhausted (memo: the free tier ~$450 evaporates within hours under swarm load). A single-cloud lock-in risks a repeat of that trap, and a single-node self-host risks availability gaps when the host is rebooted, off, or gaming (Parsec).

Constraints:

- **Zero new monthly spend** for Phase 1. Free-tier credits only.
- **Solo-dev** operational model — no on-call rotation; every node needs a kill-switch.
- **Heterogeneous workloads** — lightweight webhook fanout, medium CI jobs, heavy `cargo build --workspace`, GPU-adjacent ML.
- **Network trust** — prefer a managed WireGuard overlay over raw public IPs.

## Decision

Deploy a **7-node hybrid compute mesh** combining always-on cloud free-tier nodes with a high-powered home desktop over a Tailscale control plane. The nodes are:

| # | Provider | Role | Always-on? |
|---|----------|------|------------|
| 1 | Oracle Cloud (Ampere A1, primary) | Forgejo git host + Woodpecker CI server + Vaultwarden | Yes |
| 2 | Oracle Cloud (Ampere A1, secondary) | Woodpecker agent, medium-weight CI | Yes |
| 3 | GCP e2-micro | Tertiary CI runner, DNS/observability sidecar | Yes |
| 4 | AWS Lambda + API Gateway | Webhook fanout from GitHub → Forgejo mirror | On demand |
| 5 | Cloudflare Workers + Tunnel | Public edge for Forgejo, Vaultwarden; R2 mirror (Phase 2) | Yes |
| 6 | Home Mac (Tailscale-attached) | **Heavy** runner — cargo release, VRAM work | When idle (Parsec-gated) |
| 7 | Hetzner (Phase 2, paid burst) | Spillover when heavy jobs queue | Provisioned on demand |

All nodes join a single Tailscale tailnet; MagicDNS provides stable names (`oci-primary`, `oci-secondary`, `gcp-e2`, `home-mac`, etc.). Forgejo is the canonical git host; GitHub is a public mirror.

## Consequences

**Positive**

- Zero new spend in Phase 1 (all free tiers + existing hardware).
- Redundancy: if OCI primary goes down, OCI secondary + GCP e2-micro continue serving.
- Heavy-build latency drops ~5x (home Mac vs. OCI Ampere on `cargo build --release`).
- Public exposure limited to Cloudflare Tunnel; no origin IP leaks.

**Negative**

- Operational surface area is larger than a single cloud.
- Home-Mac availability is gated on Parsec / gaming sessions (see ADR 0008).
- Tailscale is a single point of trust (see ADR 0004 for mitigation).
- Vendor-lock risk spread across 4 providers — each has its own Terraform provider to maintain.

**Neutral**

- Requires per-node runbooks (see `docs/runbooks/`).
- Requires label-based runner routing (see ADR 0007).

## Alternatives considered

1. **Single Hetzner dedicated box (~€40/mo).** Rejected: violates zero-spend Phase-1 constraint; lock-in; no redundancy.
2. **GitHub Actions + paid minutes.** Rejected: account has a documented billing freeze; costs scale with swarm agent count (hit $450 in hours).
3. **Kubernetes on OCI free tier.** Rejected: k8s operational overhead is not justified for a 7-node solo-dev mesh; runbooks become fragile.
4. **Nomad + Consul cluster.** Rejected: same argument as k8s; Forgejo + Woodpecker + Tailscale achieves the goal with far fewer moving parts.
5. **All-in on home desktop.** Rejected: single point of failure; Parsec/gaming makes availability unpredictable; no public surface.

## Related

- ADR 0002 — OCI as primary backbone
- ADR 0003 — Home desktop as heavy runner
- ADR 0004 — Tailscale as control plane
- Spec: `docs/specs/compute-mesh-spec.md`
