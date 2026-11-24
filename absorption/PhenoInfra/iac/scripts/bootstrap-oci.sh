#!/usr/bin/env bash
# Justification (scripting policy, ~/.claude/CLAUDE.md): 5-line glue orchestrator that
# chains `terraform apply` + `ansible-playbook` — the real logic lives in those tools;
# a Rust wrapper would add no value over this ≤5-line dispatch.
set -euo pipefail
(cd "$(dirname "$0")/../terraform/oci" && terraform init && terraform apply)
(cd "$(dirname "$0")/../ansible" && ansible-playbook playbooks/install-forgejo.yml playbooks/install-vaultwarden.yml playbooks/install-woodpecker.yml --limit oci-primary)
