# Rollback and Kill-Switch Specification

Every node and every major component has a documented path to disable or revert. Solo-dev operations means we cannot afford an outage with no escape.

## Global kill-switch — revert all CI to GitHub Actions

If the entire Forgejo + Woodpecker mesh becomes unavailable:

1. In each Phenotype repo, `.woodpecker.yml` has a twin `.github/workflows/fallback.yml` (gated on repo variable `USE_GH_ACTIONS=1`).
2. Run the helper (Phase-2 TODO, Rust) `iac/scripts/kill-switch.rs` against the org — it sets `USE_GH_ACTIONS=1` on every repo via the GitHub API.
3. CI resumes on GitHub Actions (billing permitting). Accept the cost for emergency use.

## Per-node rollback

| Node | Disable procedure | Blast radius |
|------|-------------------|--------------|
| oci-primary | Stop Forgejo + Vaultwarden systemd units; Cloudflare Tunnel auto-fails over to secondary if configured | Git write + CI + secrets unavailable |
| oci-secondary | Drain Woodpecker agent; stop systemd unit | CI capacity −~50% |
| gcp-e2 | Drain Woodpecker agent; `gcloud compute instances stop` | CI capacity −~20% |
| aws-lambda | `terraform destroy -target=module.aws_lambda` | Webhook fanout lost; public → Forgejo mirror stops updating |
| cf-edge | Cloudflare dashboard: pause tunnel; route to maintenance page Worker | Public access lost; internal unaffected |
| home-mac | `launchctl unload ~/Library/LaunchAgents/com.phenotype.woodpecker-agent.plist` | Heavy jobs queue indefinitely |
| hetzner-burst (P2) | `terraform destroy -target=module.hetzner` | Paid burst lost; free mesh unaffected |

## Rollback triggers (when to pull)

- **Tailscale control-plane compromise:** rotate all Tailscale auth keys, revert to WireGuard raw configs (emergency configs stored in Vaultwarden `tailscale/emergency-wg-configs`).
- **Forgejo data corruption:** restore from nightly snapshot on oci-secondary; Phase 2 adds R2 off-site copy.
- **Home-Mac compromise:** revoke Tailscale node, revoke Woodpecker agent secret, rotate any creds fetched in last 24h.
- **Cloud provider account lock:** the multi-cloud design means any single lock leaves ≥5 nodes functional; rebuild the locked provider from Terraform.

## Verification schedule

- Monthly: run `iac/scripts/health-check.sh` (cross-node Tailscale ping + service HTTP probe).
- Quarterly: dry-run the global kill-switch against a single test repo.
- Per-ADR change: validate that rollback procedure for affected node is still accurate.

## Related

- `docs/governance/incident-response.md`, `docs/specs/credential-inventory.md`
