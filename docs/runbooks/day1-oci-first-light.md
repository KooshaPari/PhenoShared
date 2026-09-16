# Day 1 — OCI Ampere First Light

Bring up `oci-primary` and `oci-secondary` from zero to running Forgejo + Vaultwarden + Woodpecker server.

**Estimated wall-clock:** ~2 hours (mostly terraform apply + ansible convergence).

## Prerequisites

- OCI account with Always Free tier available, region chosen (e.g., `us-phoenix-1`).
- API signing key uploaded, credentials OCID-01 / OCID-02 captured in Vaultwarden (`oci/terraform-admin`).
- Cloudflare account + zone for public ingress (can be added later).
- Tailscale OAuth client (`tailscale/oauth-client` in Vaultwarden).
- Local tooling: `terraform >= 1.7`, `ansible >= 2.15`, `bw` CLI logged in.

## Step 1 — Provision VMs

> ⚠️ **A1.Flex capacity warning.** OCI Always-Free Ampere routinely returns
> `Out of host capacity` for hours or days at a time. Do **not** sit on a
> blocking `terraform apply` and refresh by hand. Instead, run the
> [`iac/oci-lottery`](../../iac/oci-lottery/README.md) Rust daemon, which
> polls `oci compute instance launch` across configured regions on a
> 2-minute jittered interval until Oracle hands out capacity, then fires a
> post-acquire hook chain (see
> [`iac/oci-post-acquire/oci-post-acquire.sh`](../../iac/oci-post-acquire/oci-post-acquire.sh)
> and [`iac/oci-post-acquire/hooks.d.example/`](../../iac/oci-post-acquire/hooks.d.example))
> to commit state, relay an iMessage, and hand off to the Tailscale +
> Ansible steps below.
>
> Sequence in practice: run `oci-lottery` first to obtain instances,
> **then** import them into Terraform state (or let Terraform recognize
> them via matching `display_name`) before running `terraform apply` for
> the surrounding VCN / security-list / DNS resources.

```bash
cd iac/terraform/oci
bw get notes oci/terraform-env | source /dev/stdin  # exports TF_VAR_* creds
terraform init
terraform plan -out=apply.plan
# REVIEW the plan carefully — confirms 2 A1 Flex VMs, 1 VCN, 1 security list.
terraform apply apply.plan
```

Record the public IPs and ephemeral Tailscale auth keys emitted by `terraform output`.

## Step 2 — Join Tailscale

Cloud-init in `ampere-primary.tf` runs `tailscale up --authkey=<ephemeral>` at first boot. Verify:

```bash
tailscale status | grep oci-primary
tailscale status | grep oci-secondary
```

Both should appear with recent "last seen" timestamps.

## Step 3 — Ansible convergence

```bash
cd ../../ansible
cp inventory.yml.example inventory.yml
# edit inventory.yml to point at oci-primary.<tailnet>.ts.net and oci-secondary.<tailnet>.ts.net

ansible all -m ping
# Expect: both nodes respond pong via Tailscale SSH.

ansible-playbook playbooks/install-forgejo.yml --limit oci-primary
ansible-playbook playbooks/install-vaultwarden.yml --limit oci-primary
ansible-playbook playbooks/install-woodpecker.yml --limit oci-primary
```

## Step 4 — Forgejo bootstrap

1. SSH via Tailscale: `ssh ubuntu@oci-primary`.
2. Navigate to `http://localhost:3000` over an SSH tunnel: `ssh -L 3000:localhost:3000 ubuntu@oci-primary`.
3. Complete the Forgejo install wizard; **skip** setting an admin account on the web — use CLI:
   ```
   sudo -u git forgejo admin user create --admin --username koosha --email kooshapari@gmail.com --random-password
   ```
4. Save the random password to Vaultwarden as `forgejo/admin`.
5. Mirror repos: for each Phenotype repo, create a push mirror targeting GitHub. Token: `GH-01` from Vaultwarden.

## Step 5 — Vaultwarden bootstrap

1. On oci-primary: `docker logs vaultwarden` to find the admin token; immediately rotate to a long random value via `docker-compose down && docker-compose up -d` with a new `ADMIN_TOKEN`.
2. Store the new token in 1Password (NOT Vaultwarden — chicken/egg).
3. Create a service-account-like collection for agents; generate a read-only API key (`VW-02`).

## Step 6 — Woodpecker server

1. Server reachable at `http://localhost:8000` via tunnel.
2. Configure OAuth against Forgejo (`Settings → Applications → OAuth2` in Forgejo).
3. Add `woodpecker-server` as authorized app; capture client_id/secret into Vaultwarden.
4. Restart Woodpecker server with those envs.

## Step 7 — Health check

```bash
cd iac/scripts
./health-check.sh
```

Expected output:

```
oci-primary      OK    tailscale   ping=4ms  forgejo=200  vaultwarden=200  woodpecker=200
oci-secondary    OK    tailscale   ping=3ms  (no services)
```

## Step 8 — Commit state

- `terraform.tfstate` → encrypted and stored in Vaultwarden (`oci/tfstate-primary-snapshot`), never in Git.
- Run `terraform output -json > /tmp/oci-outputs.json` and upload the non-secret bits to a private gist for reference.

## Rollback

See `docs/specs/rollback-kill-switch-spec.md` § oci-primary and § oci-secondary.
