# Incident Response

Solo-dev operational model: no on-call rotation, no paging. Incident response is manual and prioritized by severity.

## Severity definitions

| Sev | Definition | Response time goal |
|-----|------------|-------------------|
| SEV-1 | Public Forgejo down; credential compromise suspected | < 1 hour |
| SEV-2 | CI unavailable on all runners; single-provider outage | < 4 hours |
| SEV-3 | Single runner degraded; cost alarm breached | < 24 hours |
| SEV-4 | Cosmetic / observability degradation | Best effort |

## Outage playbooks

### Forgejo down (SEV-1)

1. Check oci-primary Tailscale status + systemd unit.
2. If service crashed: `sudo systemctl restart forgejo`; check logs.
3. If VM down: follow `docs/runbooks/node-rebuild-recovery.md` § oci-primary.
4. If data corrupt: restore from oci-secondary snapshot.
5. Activate global kill-switch (revert to GitHub Actions) if outage > 2h.

### Credential compromise (SEV-1)

1. Immediately rotate suspected credential (see `docs/governance/security-policy.md`).
2. Identify blast radius via audit logs (Tailscale, provider, Vaultwarden).
3. Rotate all credentials fetched by the compromised identity in last 7 days.
4. Rebuild affected node per `node-rebuild-recovery.md`.
5. Write post-incident note below.

### CI runner offline (SEV-2/3)

1. Check Woodpecker server UI → Agents panel.
2. SSH to the agent node; `systemctl status woodpecker-agent` or `launchctl list` on Mac.
3. Restart the agent; if persistent, rebuild node.
4. If all runners for a label are offline: re-label existing jobs to a different pool (manual or via queue-warden).

### Cost alarm (SEV-3)

1. Identify the breached resource from the alarm message.
2. Consult `docs/governance/cost-budget.md` — is this expected Phase-2 spend?
3. If unexpected: pause the resource, investigate the trigger (misconfigured CI loop, leaked credential, etc.).

## Rotation log

Append rotations here:

- _YYYY-MM-DD — initial keys issued during Day-1 bring-up._

## Post-incident notes

Append to this file in reverse chronological order:

```
## YYYY-MM-DD — <short title>
- Severity: SEV-N
- Trigger:
- Detection:
- Resolution:
- Follow-ups:
```

## On-call

There is no on-call. Incidents wait until the solo dev is reachable. The mesh is designed so no single failure causes permanent data loss (see `rollback-kill-switch-spec.md`).
