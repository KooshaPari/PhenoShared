# Day 2 — Cloudflare Tunnel → Forgejo Public

Expose Forgejo (and optionally Vaultwarden + Woodpecker UI) to the public internet via Cloudflare Tunnel, with no public IP on oci-primary.

**Estimated wall-clock:** ~1 hour.

## Prerequisites

- `day1-oci-first-light.md` complete.
- Cloudflare zone (`phenotype.io` or similar) active.
- Cloudflare API token `CF-01` in Vaultwarden with Tunnel + Zone permissions.

## Step 1 — Create the tunnel (Terraform)

```
cd iac/terraform/cloudflare
terraform init
terraform plan -out=tunnel.plan -target=cloudflare_tunnel.oci_primary
terraform apply tunnel.plan
```

Record the tunnel UUID and the tunnel token (stored automatically into Vaultwarden `cloudflare/tunnel-oci-primary`, key `CF-02`).

## Step 2 — Install cloudflared on oci-primary

```
ssh ubuntu@oci-primary
sudo mkdir -p /etc/cloudflared
sudo bw get notes cloudflare/tunnel-oci-primary > /etc/cloudflared/credentials.json
sudo chmod 600 /etc/cloudflared/credentials.json
sudo cp configs/cloudflared/config.yml.example /etc/cloudflared/config.yml
# edit /etc/cloudflared/config.yml: fill tunnel UUID, hostname mappings, credentials-file path
sudo systemctl enable --now cloudflared
systemctl status cloudflared
```

## Step 3 — DNS records

Terraform adds CNAME records `git.phenotype.io`, `vault.phenotype.io`, `ci.phenotype.io` pointing at `<tunnel-uuid>.cfargotunnel.com`. Verify:

```
dig +short git.phenotype.io
# Expect CNAME → <tunnel-uuid>.cfargotunnel.com
```

## Step 4 — Access controls (Cloudflare Access)

For `vault.phenotype.io` and `ci.phenotype.io`, require Cloudflare Access (OTP to kooshapari@gmail.com):

- Zero Trust → Access → Applications → Add application (self-hosted).
- Policy: `email` in `[kooshapari@gmail.com]`.
- Session duration: 24h.

Forgejo (`git.phenotype.io`) stays open to the public (mirror target) with rate limiting via Cloudflare rules.

## Step 5 — Smoke test

```
curl -I https://git.phenotype.io        # expect 200 with Forgejo Server header
curl -I https://vault.phenotype.io      # expect 302 to Cloudflare Access login
curl -I https://ci.phenotype.io         # expect 302 to Cloudflare Access login
```

## Step 6 — Update mesh spec

Append the three hostnames to `docs/specs/compute-mesh-spec.md` § Public surface.

## Rollback

- Cloudflare dashboard → Zero Trust → Tunnels → pause.
- Remove CNAME records (or point at maintenance Worker).
- On oci-primary: `sudo systemctl stop cloudflared`.
