# iac/terraform/ — provider modules (SCAFFOLD, not yet applied)

> **Status: validated scaffold. Nothing here has been `terraform apply`-ed.**
> Every resource block is intentionally **commented out** pending a credentialed
> first-apply review. These modules declare providers, variables, and (commented)
> resources so the topology is reviewable and `terraform validate`-clean — they do
> **not** stand up infrastructure as-is. Do not mistake "validates" for "deployed".

## What is real today

- **Provider + variable declarations** for each target (pinned in `providers.tf`
  and per-module). Credentials are placeholders (`<OCI_TENANCY_OCID>`, etc.),
  injected at apply time from Vaultwarden via `TF_VAR_*` — never committed.
- **Commented resource blocks** capturing the intended free-tier topology.
- **CI gate** (`.github/workflows/terraform-plan.yml`): runs `fmt -check`,
  `init -backend=false`, and `validate` on every module on each PR. `plan`/`apply`
  are **not** run in CI (no credentials by design).

## What is NOT real yet

- No resources exist in any cloud account from this code.
- No remote backend (state is snapshotted to Vaultwarden, not S3).
- `apply` is **human-only** and gated on explicit user approval (see repo README
  "Contribution rules"). Agents may `plan` and open PRs; they must not `apply`.

## Modules + free-tier intent

| Module | Provider | Free-tier target |
|--------|----------|------------------|
| `oci/` | `oracle/oci` | OCI Ampere A1.Flex (Always Free) — primary backbone |
| `gcp/` | `hashicorp/google` | `e2-micro` (Always Free tier) — tertiary runner/sentinel |
| `aws/` | `hashicorp/aws` | Lambda on Graviton (free-tier) — webhook fanout |
| `cloudflare/` | `cloudflare/cloudflare` | Tunnel + Workers (free plan) — edge surface |
| `tailscale.tf` (root) | `tailscale/tailscale` | Tailnet control plane (free tier) |

All targets are deliberately free-tier / always-free; this mesh is designed to be
**never-billable**. See ADRs 0001–0009 in `../../docs/adr/`.

## Verifying locally

```sh
# Per module (as CI does). Requires terraform 1.7.x.
cd iac/terraform/oci   # or gcp / aws / cloudflare / .
terraform fmt -check
terraform init -backend=false
terraform validate      # -> "Success! The configuration is valid."
```

All five modules (root + oci/gcp/aws/cloudflare) currently validate clean.

## Going live (human-only)

First-apply is a deliberate, credentialed step, not part of normal CI. Start from
the bring-up runbook: [`../../docs/runbooks/day1-oci-first-light.md`](../../docs/runbooks/day1-oci-first-light.md).
Uncommenting a module's resource blocks + first `apply` should land in its own
reviewed PR with the human operator present.
