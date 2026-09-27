# Credential Inventory

Complete inventory of credentials, their providers, scopes, and storage locations. All live values are in Vaultwarden; this document tracks WHAT exists, not the values.

## Inventory table

| ID | Provider | Type | Scope | Stored In | Consumed By | Rotation |
|----|----------|------|-------|-----------|-------------|----------|
| OCI-01 | Oracle Cloud | API signing key | Tenancy admin | Vaultwarden → `oci/terraform-admin` | Terraform oci provider | 180d |
| OCI-02 | Oracle Cloud | Instance SSH key | per-VM | Vaultwarden → `oci/ssh-ampere-primary`, `oci/ssh-ampere-secondary` | Ansible, human debug | 180d |
| GCP-01 | GCP | Service-account JSON | Project-scoped, runner only | Vaultwarden → `gcp/terraform-sa` | Terraform gcp provider | 180d |
| AWS-01 | AWS | IAM access key | Lambda deploy + API GW | Vaultwarden → `aws/terraform-deployer` | Terraform aws provider | 90d |
| CF-01 | Cloudflare | API token | Zone + Workers + Tunnel | Vaultwarden → `cloudflare/terraform-token` | Terraform cloudflare provider | 90d |
| CF-02 | Cloudflare | Tunnel credentials JSON | per-tunnel | Vaultwarden → `cloudflare/tunnel-oci-primary` | cloudflared daemon on oci-primary | 180d |
| TS-01 | Tailscale | OAuth client | Mesh admin | Vaultwarden → `tailscale/oauth-client` | Terraform tailscale provider | 180d |
| TS-02 | Tailscale | Ephemeral auth-key | burst nodes | Generated at runtime; 1h TTL | Terraform, cloud-init | ephemeral |
| GH-01 | GitHub | PAT (public mirror push) | repo: write on mirrored repos | Vaultwarden → `github/mirror-push` | Forgejo push-mirror | 90d |
| GH-02 | GitHub | App private key (webhook) | Webhook install | Vaultwarden → `github/webhook-app` | aws-lambda | 180d |
| FJ-01 | Forgejo | Admin password | admin | Vaultwarden → `forgejo/admin` | human only | 90d |
| FJ-02 | Forgejo | Runner registration token | per-runner | Vaultwarden → `forgejo/runner-tokens/*` | woodpecker-agent on each node | on-reprovision |
| WP-01 | Woodpecker | agent secret | per-agent | Vaultwarden → `woodpecker/agent-secrets/*` | woodpecker-agent | 180d |
| VW-01 | Vaultwarden | Admin token | admin panel | 1Password (bootstrap); rotate out | human only | 30d |
| VW-02 | Vaultwarden | Agent service-account | read-only scoped | Vaultwarden self (bootstrap via 1Password) | all agent workflows | 90d |

## Injection patterns

- **Terraform:** `TF_VAR_*` env vars sourced from `bw get` wrappers; never on disk unencrypted.
- **Ansible:** `ansible-vault` layer + Bitwarden CLI retrieval.
- **Woodpecker pipelines:** use `from_secret:` blocks referencing Woodpecker's own secret store (values mirror a subset of Vaultwarden, synced weekly).
- **Agents (LLM/coding):** fetch on demand via `bw`, in-memory only; never echoed to logs.

## Rotation procedure

See `docs/governance/security-policy.md`.

## Placeholder conventions (for docs/IaC)

When writing documentation or IaC stubs, use these placeholders (never paste real values):

- `<OCI_TENANCY_OCID>`, `<OCI_USER_OCID>`, `<OCI_FINGERPRINT>`
- `<GCP_PROJECT_ID>`, `<GCP_SA_EMAIL>`
- `<AWS_ACCOUNT_ID>`, `<AWS_REGION>`
- `<CLOUDFLARE_ACCOUNT_ID>`, `<CLOUDFLARE_ZONE_ID>`
- `<TAILSCALE_TAILNET>`, `<TAILSCALE_AUTHKEY>`
- `<GITHUB_PAT>`, `<GITHUB_APP_ID>`
