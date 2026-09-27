# Security Policy

## Scope

All Phenotype compute-mesh nodes, credentials, and agent workflows.

## SSH key rotation

- Per-node SSH keys are rotated every **180 days**.
- Rotation procedure:
  1. Generate new key pair with `ssh-keygen -t ed25519 -C "<node>-<YYYYMM>"`.
  2. Add public key via Ansible; remove old key in the same playbook run.
  3. Update Vaultwarden (`oci/ssh-<node>`).
  4. Verify access; log rotation in `docs/governance/incident-response.md` § rotation log.

## API token scoping

- All third-party tokens are scoped to the minimum permissions required. See `docs/specs/credential-inventory.md` for per-token scopes.
- Rotate every **90 days** for API tokens; every **180 days** for OAuth client secrets and service-account keys.
- On compromise suspicion: **immediate rotation** + incident note.

## MFA

- GitHub, AWS, GCP, Cloudflare, Oracle Cloud, Tailscale, Vaultwarden admin — all MFA-enforced (TOTP + backup codes stored in a paper envelope).
- 1Password bootstrap vault uses a hardware key (YubiKey) where available.

## Agent credential handling

- Agents fetch creds from Vaultwarden via `bw` CLI, in-memory only.
- Agents MUST NOT echo credentials to chat output, commit messages, logs, or files.
- Every agent workflow that touches a credential is audited in `AGENTS.md` § workflows that touch production.

## Network security

- All inter-node traffic on Tailscale overlay.
- Public ingress exclusively via Cloudflare Tunnel (no public IPs on backbone).
- Cloudflare Access gates Vaultwarden and Woodpecker UI; Forgejo public is rate-limited + WAF-inspected.

## Backup + disaster recovery

- Forgejo: nightly `forgejo dump` → oci-secondary filesystem → (Phase 2) Cloudflare R2 off-site.
- Vaultwarden: nightly `sqlite3 .backup` → encrypted tarball → oci-secondary → (Phase 2) R2.
- Terraform state: per-apply snapshot → Vaultwarden `*/tfstate-snapshot`. Never in Git.

## Audit

- Tailscale admin log retained 90 days.
- Cloudflare audit log reviewed monthly.
- Cloud provider audit logs enabled (OCI Audit, GCP Cloud Audit Logs, AWS CloudTrail).

## Related

- `docs/specs/credential-inventory.md`, `docs/governance/incident-response.md`
