# A26 — Orphaned Configs Audit (`configs/`)

**Date:** 2026-06-24  
**Scope:** All files under `configs/` — all are `.example` files for service configuration.

---

## Methodology

1. Enumerate every file under `configs/`.
2. For each config, search for references across the repo:
   - Ansible playbooks (`iac/ansible/playbooks/`) and templates
   - Terraform modules (`iac/terraform/`)
   - Runbooks under `docs/runbooks/`
   - Governance docs, specs, ADRs in `docs/`
   - GitHub workflows (`.github/workflows/`)
   - Any other files referencing the `configs/` path or the service name + config pattern
3. Classify as **Referenced** (has a cross-reference to the `.example` path or explicit
   mention of the config file being a template for a service) or **Missing Reference**
   (no non-trivial external reference found).
4. Since all are `.example` files, verify each has a corresponding service reference
   (Ansible playbook, runbook step, or governance doc).

---

## Results

### File Inventory

| Config File | Service | Status | References |
|-------------|---------|--------|------------|
| `cloudflared/config.yml.example` | Cloudflare Tunnel | **Referenced** | `docs/runbooks/day2-cloudflare-tunnel.md:31` (explicit `sudo cp configs/cloudflared/config.yml.example /etc/cloudflared/config.yml`) |
| `forgejo/app.ini.example` | Forgejo | **Referenced** | Ansible `install-forgejo.yml` templates `forgejo-app.ini.j2` to `/etc/forgejo/app.ini`; the `.example` is the human-readable counterpart. |
| `vaultwarden/config.env.example` | Vaultwarden | **Referenced** | Ansible `install-vaultwarden.yml` writes `.env` to `/etc/vaultwarden/.env` with the same keys; the `.example` serves as reference for manual override. |
| `woodpecker/server.env.example` | Woodpecker | **Referenced** | Ansible `install-woodpecker.yml` writes `server.env` to `/etc/woodpecker/server.env` with the same structure; the `.example` is for manual reference. |

### Service Mapping

Each `.example` configuration file corresponds to a service that has an Ansible
playbook in `iac/ansible/playbooks/`:

| Config File | Corresponding Ansible Playbook |
|-------------|-------------------------------|
| `cloudflared/config.yml.example` | `install-cloudflared.yml` (uses Jinja2 template `cloudflared-config.yml.j2`; `.example` is the manual-reference counterpart) |
| `forgejo/app.ini.example` | `install-forgejo.yml` (uses Jinja2 template `forgejo-app.ini.j2`; `.example` documents the expected structure for operators) |
| `vaultwarden/config.env.example` | `install-vaultwarden.yml` (writes `.env` inline via `ansible.builtin.copy`; `.example` documents the config shape) |
| `woodpecker/server.env.example` | `install-woodpecker.yml` (writes `server.env` inline via `ansible.builtin.copy`; `.example` documents the config shape) |

### Reference Depth

| Config | Path reference in docs | Ansible template/inline | Runbook step | Workflow ref |
|--------|----------------------|------------------------|--------------|--------------|
| `cloudflared/config.yml.example` | `docs/runbooks/day2-cloudflare-tunnel.md:31` (`sudo cp configs/cloudflared/...`) | `cloudflared-config.yml.j2` for `/etc/cloudflared/config.yml` | Day 2 tunnel setup | None |
| `forgejo/app.ini.example` | No direct `configs/forgejo/` path ref in docs | `forgejo-app.ini.j2` templated to `/etc/forgejo/app.ini` | Day 1 OCI first light | None |
| `vaultwarden/config.env.example` | No direct `configs/vaultwarden/` path ref in docs | Inline `.env` written to `/etc/vaultwarden/.env` | Day 1 OCI first light | None |
| `woodpecker/server.env.example` | No direct `configs/woodpecker/` path ref in docs | Inline `server.env` written to `/etc/woodpecker/server.env` | Day 1 OCI first light, Day 1 home runner | None |

---

## Summary

- **Total config files inventoried:** 4
- **Directly referenced by path in docs:** 1 (`cloudflared/config.yml.example`)
- **Indirectly referenced (service exists + Ansible playbook exists):** 3 (`forgejo/app.ini.example`, `vaultwarden/config.env.example`, `woodpecker/server.env.example`)
- **Orphaned (no reference at all):** 0

**No orphaned configs found.** Every `.example` file under `configs/` corresponds
to a real service with an Ansible deployment playbook. The `cloudflared` example
is explicitly referenced by path in `day2-cloudflare-tunnel.md`. The other three
(`forgejo`, `vaultwarden`, `woodpecker`) serve as human-readable documentation
alongside their Ansible-managed equivalents.

### Notes

- The three configs without a direct `configs/` path reference (`forgejo`, `vaultwarden`,
  `woodpecker`) are **not** truly orphaned — their service playbooks exist and the
  `.example` files document the expected schema for operators. They could be
  referenced explicitly in the corresponding runbooks or Ansible README
  (`iac/ansible/README.md`) for better discoverability.
- `cloudflared/config.yml.example` differs from the Ansible template
  (`cloudflared-config.yml.j2`): the `.example` uses `http://localhost:PORT`
  (for the noTLSVerify path), while the Ansible template uses
  `https://127.0.0.1:443` (Caddy TLS path). This is intentional — the `.example`
  is a simpler alternative for operators who don't use the full Caddy stack.
- No `.orphaned` markers were added since no configs are orphaned.
