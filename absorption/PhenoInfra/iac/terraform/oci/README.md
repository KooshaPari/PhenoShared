# iac/terraform/oci/

Terraform module for Oracle Cloud Ampere A1 Flex backbone VMs.

## Files

- `ampere-primary.tf` — oci-primary (Forgejo + Vaultwarden + Woodpecker server).
- `ampere-secondary.tf` — oci-secondary (CI agent, metrics, backup target).

## Usage

```
cd iac/terraform/oci
bw get notes oci/terraform-env | source /dev/stdin
terraform init
terraform plan -out=apply.plan
terraform apply apply.plan   # HUMAN ONLY — per AGENTS.md
```

See `docs/runbooks/day1-oci-first-light.md` for the full bring-up procedure.

## Status

Resource blocks are commented out; review and uncomment during first apply.
