# iac/ — Phenotype Infra Operational Crates

Infrastructure-as-code root. Holds Terraform/Ansible domain assets **and**
the Rust operational crates that orchestrate them. Per the Phenotype
scripting policy, persistent loops, retry daemons, and codegen live in
Rust; Terraform and Ansible remain canonical for declarative state.

## Operational crates

| Crate | Role | Entry point |
|-------|------|-------------|
| [`oci-lottery`](./oci-lottery/README.md) | A1.Flex capacity-lottery daemon. Polls `oci compute instance launch` across regions with jittered backoff until Oracle releases capacity, then fires the post-acquire chain. Replaces ad-hoc `while; do oci ...; sleep 120; done` shell loops. | `oci-lottery` (binary, plist in `dist/`) |
| [`oci-post-acquire`](./oci-post-acquire) | Post-acquire hook orchestrator invoked by `oci-lottery` on success. Runs ordered hooks from `hooks.d/` to commit state, notify, and chain into Tailscale join + Ansible convergence. | `oci-post-acquire.sh` + `hooks.d.example/` |
| [`tailscale/tailscale-keygen`](./tailscale/tailscale-keygen) | Mints ephemeral, pre-authorized Tailscale auth keys via the Tailscale API for cloud-init bootstrapping. Replaces interactive `tailscale up` flows on first boot. | `tailscale-keygen` (binary) |
| [`landing-bootstrap`](./landing-bootstrap/README.md) | Generates the per-node landing/handoff page (Forgejo + Vaultwarden + Woodpecker links, runbook crossrefs) from a template after a node is acquired and converged. | `landing-bootstrap` (binary) |

## Domain-tool directories

| Directory | Contents |
|-----------|----------|
| `terraform/` | Per-provider modules (OCI, GCP, AWS, Cloudflare). Apply is human-only; plan can be agent-driven. |
| `ansible/` | Convergence playbooks (Forgejo, Vaultwarden, Woodpecker, Tailscale). |
| `scripts/` | Bootstrap helpers — Rust binaries or ≤5-line bash glue with justification comments. |
| `data/` | Static fixtures and seed data referenced by the crates. |

## Day-1 entry point

For a fresh OCI mesh bring-up, start at
[`docs/runbooks/day1-oci-first-light.md`](../docs/runbooks/day1-oci-first-light.md).
The runbook references `oci-lottery` and `oci-post-acquire` directly at the
A1.Flex provisioning step; do not run a blocking `terraform apply` against
A1.Flex without the lottery daemon in front of it.
