# ADR 0002 — OCI Ampere as Primary Backbone

- **Status:** Accepted
- **Date:** 2026-04-24

## Context

Per ADR 0001, the mesh requires an always-on backbone that hosts Forgejo (git), Woodpecker (CI orchestrator), and Vaultwarden (credential store). Requirements:

- Always-on with generous free-tier bandwidth.
- At least 4 vCPU / 24 GiB RAM across the backbone tier to accommodate concurrent Woodpecker pipelines without thrashing.
- Arm64 is acceptable (most workloads cross-compile cleanly).
- Provider must support Terraform-driven provisioning end-to-end.

## Decision

Use **two Oracle Cloud Ampere A1 Flex VMs** as the primary backbone:

- **oci-primary:** 2 OCPU (4 vCPU-equivalent) / 12 GiB RAM. Hosts Forgejo, Vaultwarden, Woodpecker server, Cloudflare Tunnel client.
- **oci-secondary:** 2 OCPU / 12 GiB RAM. Hosts Woodpecker agent #1, metrics (Prometheus + Grafana), backup target for Forgejo data.

Both sit inside a single VCN with a tight security list (only Tailscale + SSH from a known jump IP). Public ingress comes exclusively via Cloudflare Tunnel (ADR 0004 dependency).

## Consequences

**Positive**

- 4 OCPU + 24 GiB RAM total is ample for 30-repo CI + git hosting.
- OCI Always Free tier includes these A1 Flex shapes indefinitely (as of 2026-04).
- Arm64 builds match home-Mac architecture (Apple Silicon), easing cross-compilation.
- Bandwidth: OCI provides 10 TB/mo outbound free — far above projected use.

**Negative**

- OCI's reputation for reclaiming "idle" free-tier VMs — mitigated by running a lightweight cron that keeps CPU above reclamation threshold (documented in `docs/runbooks/day1-oci-first-light.md`).
- Arm64 can break x86-only dependencies — mitigated by pinning `rust-musl-cross-aarch64` and `cargo-zigbuild`.
- Console UX is hostile; rely on Terraform + Ansible.

## Alternatives considered

1. **Hetzner CAX11 Arm VM (~€3.29/mo).** Close second; rejected to preserve zero-spend Phase 1. Kept as Phase-2 spillover candidate.
2. **AWS t4g.small free tier (12 mo only).** Rejected: 12-month clock causes future migration burden.
3. **GCP e2-micro alone.** Rejected: 1 GiB RAM insufficient for Forgejo + Vaultwarden co-location.

## Related

- ADR 0001 (mesh), ADR 0005 (Forgejo choice), ADR 0006 (Vaultwarden), `iac/terraform/oci/`
