# phenotype-infra / ansible

Playbooks that bring an Oracle Linux 8 ARM64 OCI Ampere VM from `ssh opc@<ip>`
to a running Forgejo + Woodpecker + Vaultwarden stack fronted by Caddy and
exposed via Cloudflare Tunnel.

## Prereqs (once, locally)

1. OCI Ampere VM provisioned (blocked on capacity availability) — ensure
   `~/.ssh/oci_ampere_phenotype` can reach it as `opc`.
2. Tailscale ephemeral auth key: https://login.tailscale.com/admin/settings/keys
3. Cloudflare API token, scope `Zone:DNS:Edit` on `kooshapari.com`.
4. Cloudflare Tunnel pre-created locally:

   ```
   cloudflared tunnel login
   cloudflared tunnel create phenotype-oci-primary
   # Note the UUID and capture the ~/.cloudflared/<UUID>.json contents.
   cloudflared tunnel route dns phenotype-oci-primary forgejo.kooshapari.com
   cloudflared tunnel route dns phenotype-oci-primary ci.kooshapari.com
   cloudflared tunnel route dns phenotype-oci-primary vault.kooshapari.com
   cloudflared tunnel route dns phenotype-oci-primary grafana.kooshapari.com
   ```

5. `cp inventory.yml.example inventory.yml` and set the OCI public IP (first
   run, pre-tailnet) or the MagicDNS name (subsequent runs).
6. `cp group_vars/oci_primary.yml.example group_vars/oci_primary.yml` and fill
   in all `<PLACEHOLDER_*>` values. Prefer `ansible-vault encrypt` for this
   file.

## Run

Full stack, one shot:

```
ansible-playbook -i inventory.yml playbooks/site.yml
```

Single service (e.g. re-apply Caddy config after editing the template):

```
ansible-playbook -i inventory.yml playbooks/install-caddy.yml
```

## First-run follow-ups

After the initial `site.yml`:

1. `ssh opc@oci-primary sudo cat /root/.forgejo-admin-password` — admin bootstrap password.
2. Log in to `https://forgejo.kooshapari.com`, change password, register an
   OAuth2 application for Woodpecker (redirect URI: `https://ci.kooshapari.com/authorize`).
3. Put the client id/secret into `group_vars/oci_primary.yml` and re-run
   `install-woodpecker.yml` to pick them up.
4. Visit `https://vault.kooshapari.com/admin` with the token from
   `/etc/vaultwarden/.admin_token` to create the first user invitation.

## Playbook order (enforced by `site.yml`)

1. `common.yml` — dnf baseline, repos, firewall, 4GB swap, tailscale + cloudflared binaries.
2. `install-tailscale.yml` — `tailscale up` with ephemeral auth key.
3. `install-caddy.yml` — xcaddy build with `caddy-dns/cloudflare` plugin, Caddyfile.
4. `install-cloudflared.yml` — tunnel credentials + systemd.
5. `install-forgejo.yml` — binary, `app.ini`, first-run admin user.
6. `install-woodpecker.yml` — server + agent, shared secret generated.
7. `install-vaultwarden.yml` — binary + web-vault + admin token.

## Design decisions flagged for review

- **Caddy via xcaddy build** (not upstream RPM) because `caddy-dns/cloudflare`
  isn't bundled. Flip `caddy_use_xcaddy: false` in `install-caddy.yml` to use
  the upstream RPM + plain-http behind cloudflared.
- **cloudflared → https://127.0.0.1:443 with `noTLSVerify: true`**. Keeps the
  loopback hop encrypted at the cost of a self-signed-style SNI mismatch.
  Alternative: tunnel to `http://127.0.0.1:80` and let CF-edge terminate only.
- **First-run admin password** is written to `/root/.forgejo-admin-password`
  (mode 0600) instead of being surfaced via Ansible stdout. Rotate after first
  login.
- **Woodpecker OAuth placeholders**: Forgejo must be up before OAuth client
  registration, so first `site.yml` run leaves Woodpecker unable to auth
  until step 3 of "first-run follow-ups".
