# Tailscale Policy

**Status:** Active (2026-04-25)
**Owner:** koosha@gmail.com
**Scope:** Phenotype compute mesh (OCI / GCP / AWS / Vercel build runners / home desktop)

This is the canonical governance doc for the Tailscale tailnet that ties the
Phenotype compute mesh together. It backs the OCI post-acquire hook chain
(see `iac/oci-post-acquire/`, PR #14) and any future bootstrap workflow that
needs to enroll a fresh node unattended.

---

## 1. Why Tailscale

Previous topology used a per-VM OCI public IP + cloud-firewall ingress rule +
WireGuard tunnel maintained by hand. Failure modes:

- **Acquisition latency:** the OCI lottery wins a VM at unpredictable times;
  manually configuring its firewall + tunnel before reuse adds 10–30 min.
- **Tunnel sprawl:** WireGuard configs were per-pair, O(n²) to maintain.
- **Auth weak spot:** SSH was guarded only by cloud-firewall IP allowlist,
  meaning a compromised home-desktop IP exposed the whole mesh.

Tailscale fixes all three: nodes self-enroll via short-lived auth-key, mesh
membership is the auth boundary (not IP), and ACL/SSH policy is one JSON file
under git.

## 2. Tag Taxonomy

| Tag | Purpose | Owner |
|---|---|---|
| `tag:phenotype-mesh` | Default mesh membership; any node tagged here can talk to any other on all ports. | koosha@gmail.com |
| `tag:oci` | Oracle Cloud Always-Free VMs (post-acquire hook). | koosha@gmail.com |
| `tag:gcp` | Google Cloud nodes. | koosha@gmail.com |
| `tag:aws` | AWS nodes. | koosha@gmail.com |
| `tag:vercel-build` | Vercel build-time runners enrolling for private-registry pulls. Short-lived. | koosha@gmail.com |
| `tag:home-desktop` | Admin workstation. Allowed to SSH into the mesh. | koosha@gmail.com |

Tag owners are declared in `iac/tailscale/acl.json` under `tagOwners`. Adding
a tag requires a PR that updates both this table and the ACL.

## 3. ACL Summary

Source of truth: `iac/tailscale/acl.json`.

- `tag:phenotype-mesh` ↔ `tag:phenotype-mesh` on all ports (full mesh).
- `koosha@gmail.com` user → all mesh nodes, all ports (admin override).
- No `autogroup:internet` rules; no public-port rules.
- SSH: only `tag:home-desktop` + `koosha@gmail.com` may SSH the mesh; check
  period 24h (Tailscale prompts for re-auth daily, no password).

## 4. Key Rotation

| Key type | Rotation cadence | Mechanism |
|---|---|---|
| Tailscale **API key** (`TS_API_KEY`, used by `tailscale-keygen`) | 90 days | Manual: koosha rotates in admin console, updates Vaultwarden + GitHub Actions secret. |
| Per-node **auth-key** (minted by `tailscale-keygen`) | 600s TTL, single-use, ephemeral | Automatic: minted on demand by post-acquire hook; node deregisters when offline. |
| **Node identity** itself | On expiry of node key (180d default) or on incident | Tailscale prompts re-auth via admin console; ephemeral nodes simply re-enroll. |

## 5. Key Issuance Flow

```
oci-post-acquire (hook)
        │
        ▼
tailscale-keygen   ◀── reads TS_API_KEY, TS_TAILNET from env
        │              (Rust binary, iac/tailscale/tailscale-keygen)
        │              POST /api/v2/tailnet/{tailnet}/keys
        ▼
single-use auth-key (TTL 600s, ephemeral=true, preauthorized=true,
                     tags=[tag:phenotype-mesh, tag:oci])
        │
        ▼
oci-post-acquire SSHes to fresh VM, runs `tailscale up --auth-key=$KEY`
```

**Who may invoke `tailscale-keygen`:**
- The post-acquire hook chain (runs as koosha on the orchestrator host).
- koosha, manually, for ad-hoc enrollments.
- No CI job. CI runners that need mesh access should use `tag:vercel-build`
  with their own ephemeral keys minted by an explicit human-approved workflow.

**Audit log:** every invocation logs (to stderr, captured by the hook chain)
the URL, tags, and TTL — but never the resulting key. Keys appear in stdout
only, captured by `$()` substitution. Tailscale-side, every minted key is
visible under Admin → Settings → Keys with description
`phenotype/<primary-tag> auto-mint by tailscale-keygen`.

## 6. Disaster Recovery

### Compromised node
1. Tailscale Admin Console → Machines → select node → **Remove**.
2. Revoke any non-ephemeral keys associated.
3. Investigate via post-acquire mesh-state log
   (`docs/compute-mesh-state.md`) — what tags did it hold, what reachable
   peers existed.
4. If the node was an OCI lottery win, terminate the underlying VM via
   `iac/oci-lottery` rather than relying on ephemeral expiry.

### Compromised `TS_API_KEY`
1. Rotate immediately in Tailscale admin console (revoke old → mint new).
2. Update Vaultwarden entry `tailscale/api-key`.
3. Update GitHub Actions secret if any workflow references it.
4. Audit recent key-mint history; any node minted in the suspicious window
   should be removed and re-enrolled.

### Compromised auth-key (the short-lived one)
- Single-use + 600s TTL means the practical blast radius is one node
  enrollment within a 10-min window. Treat as a compromised node (above).

## 7. References

- ACL source: `iac/tailscale/acl.json`
- Apply tool: `iac/tailscale/apply-acl.sh`
- Keygen: `iac/tailscale/tailscale-keygen/`
- Consumer: `iac/oci-post-acquire/` (PR #14)
- Mesh state: `docs/compute-mesh-state.md`
- Security baseline: `docs/governance/security-policy.md`
- Incident playbook: `docs/governance/incident-response.md`
