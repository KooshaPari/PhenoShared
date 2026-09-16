# Runbook — Node Rebuild / Recovery

Generalized procedure to rebuild any of the 7 mesh nodes from scratch.

## Decision matrix

| Symptom | First action |
|---------|--------------|
| Node unresponsive, Tailscale "offline" > 10 min | SSH via provider console, check logs |
| Node responsive but service failing | Restart service; check `systemctl status` |
| Node compromised / creds leaked | Rebuild from scratch (this doc) |
| Provider account locked | Rebuild on alternate provider (see multi-cloud design) |

## Rebuild procedure (generic)

1. **Quarantine.** Revoke the node's Tailscale authorization in the admin console. Revoke its Woodpecker agent secret. Rotate any credentials it had access to in the last 7 days.
2. **Destroy.** `terraform destroy -target=module.<node>` (or provider console delete).
3. **Recreate.** `terraform apply` the same module. Ensure a fresh ephemeral Tailscale auth key is issued.
4. **Re-converge.** Run the relevant Ansible playbook (e.g., `install-forgejo.yml` for oci-primary).
5. **Restore state** (if applicable):
   - Forgejo: restore from nightly snapshot on oci-secondary.
   - Vaultwarden: restore from encrypted backup on oci-secondary (and Phase-2 R2 off-site).
   - Woodpecker: state rebuilds from Forgejo; pipelines re-trigger on next push.
6. **Re-register CI.** Issue a fresh runner token from Forgejo (`FJ-02`), update Vaultwarden, re-register agent.
7. **Health check.** `iac/scripts/health-check.sh` — all green.
8. **Post-incident.** Write an incident note in `docs/governance/incident-response.md`.

## Per-node specifics

| Node | Time-to-recover | Data to restore |
|------|-----------------|-----------------|
| oci-primary | ~1h | Forgejo repos, Vaultwarden, Woodpecker config |
| oci-secondary | ~30m | Prometheus metrics (acceptable loss), backup snapshots |
| gcp-e2 | ~15m | None (stateless runner) |
| aws-lambda | ~15m | None (stateless) |
| cf-edge | ~30m | Tunnel credentials, Worker scripts (in Terraform) |
| home-mac | ~30m | Local target/ cache (regenerable) |
| hetzner-burst | ~15m | None (stateless) |

## Related

- `docs/specs/rollback-kill-switch-spec.md`
- `docs/governance/incident-response.md`
