# Day 2 — GCP e2-micro Tertiary Runner

Bring up `gcp-e2` as a lightweight always-on runner and uptime sentinel.

**Estimated wall-clock:** ~30 min.

## Prerequisites

- GCP project with billing enabled (e2-micro is in free tier, but billing must be linked).
- `GCP-01` service account key in Vaultwarden.
- Tailscale OAuth client available.

## Step 1 — Terraform apply

```
cd iac/terraform/gcp
bw get notes gcp/terraform-env | source /dev/stdin
terraform init
terraform plan -out=gcp.plan
terraform apply gcp.plan
```

The plan creates one e2-micro VM in `us-west1` (free-tier region) with a startup script that installs Tailscale and the Woodpecker agent.

## Step 2 — Verify Tailscale + runner

```
tailscale status | grep gcp-e2
ssh ubuntu@gcp-e2 'systemctl status woodpecker-agent'
```

## Step 3 — Add uptime sentinel

Install a tiny Rust uptime-probe binary that pings every mesh node every 60 s and exposes Prometheus metrics:

```
ansible-playbook playbooks/install-uptime-sentinel.yml --limit gcp-e2  # TODO: playbook stub
```

## Step 4 — Smoke

Run a light CI job labeled `[self-hosted, oci, medium]` (gcp-e2 advertises the medium label):

```yaml
steps:
  smoke: { image: rust:1.80, commands: [cargo --version], runs-on: [self-hosted, oci, medium] }
```

## Rollback

- `gcloud compute instances stop gcp-e2 --zone us-west1-a`
- Or full teardown: `terraform destroy -target=module.gcp_e2`
