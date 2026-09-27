# OCI Post-Acquire Hook Chain

**Status:** scaffold (no live runs yet)
**Owner:** phenotype-infra
**Trigger:** `oci-lottery` writes `~/.cloudprovider/oci-instance.json` on success and invokes `~/.local/bin/oci-post-acquire.sh`
**Goal:** A1.Flex node fully joined to Phenotype mesh in **<5 minutes**, no human typing.

## Chain

```mermaid
flowchart TD
    L[oci-lottery wins capacity] -->|writes oci-instance.json| W[~/.local/bin/oci-post-acquire.sh]
    W --> R[oci-post-acquire (Rust)]
    R --> S1[1. Read oci-instance.json]
    S1 --> S2[2. Wait for SSH (nc :22, 90s)]
    S2 --> S3[3. Tailscale enroll<br/>POST /api/v2/.../keys]
    S3 --> S4[4. Ansible baseline<br/>iac/ansible/playbooks/oci-baseline.yml]
    S4 --> S5[5. Cloudflare A record<br/>oci-1.kooshapari.com]
    S5 --> S6[6. Mesh-state commit<br/>compute-mesh-state.md]
    S6 --> S7[7. Notify<br/>iMessage + worklog]
    S7 --> S8[8. Drop-in hooks<br/>~/.config/phenotype/oci-acquire-hooks.d/*]
    S8 --> D[Mesh node live]
```

## Step-by-step

| # | Step | Tool | Idempotent? | Failure mode |
|---|------|------|-------------|--------------|
| 1 | Read `oci-instance.json` | core | yes | abort chain — nothing to act on |
| 2 | Wait for SSH on `:22` | core (`tokio::net::TcpStream`) | yes | abort if 90s elapsed; node likely DOA |
| 3 | Tailscale enroll | `tailscale.rs` + ssh | yes (ephemeral keys) | warn-and-continue; node lacks mesh peer until re-run |
| 4 | Ansible baseline | `ansible-playbook` | yes | abort — partial baseline must be reconciled |
| 5 | Cloudflare A upsert | `cf.rs` | yes (PUT existing or POST new) | warn-and-continue; manual `dig`+upsert if missed |
| 6 | Mesh-state commit | `mesh.rs` + `git` | yes (replaces auto-insert block) | warn-and-continue; manual commit |
| 7 | Notify (iMessage + worklog) | `agent-imessage` (failsoft) | yes (append-only) | warn-and-continue |
| 8 | Drop-in hooks | every exec in `oci-acquire-hooks.d/` | hook-defined | warn per hook; chain returns ok |

## Idempotency contract

- Re-running `oci-post-acquire` on the same `oci-instance.json` MUST be safe.
  - Tailscale uses ephemeral, single-use auth-keys — re-run mints a new key; the prior one expires in 10 min.
  - Ansible playbook `oci-baseline.yml` is fully task-idempotent.
  - Cloudflare upsert PUTs over existing record id.
  - Mesh-state commit replaces any prior `<!-- oci-post-acquire: AUTO-INSERTED -->` block before committing — no duplicate sections.
  - Drop-in hooks MUST be idempotent (documented in `hooks.d/README.md`).

## Partial-success recovery

| If failure at step | Recovery |
|--------------------|----------|
| 2 (SSH wait) | Wait + check OCI console; the daemon already wrote `oci-instance.json`, so re-run once SSH responds. |
| 3 (Tailscale) | Re-run only `oci-post-acquire`; Tailscale step is idempotent. Or `ssh ubuntu@<ip>` and run `tailscale up` manually. |
| 4 (Ansible) | Inspect with `ansible-playbook --check`; fix the offending task; re-run. Baseline tasks are designed to converge. |
| 5 (DNS) | `curl -X POST .../dns_records` manually with `~/.cloudflare-token`. |
| 6 (mesh commit) | `git -C ~/CodeProjects/Phenotype/repos/phenotype-infra add docs/governance/compute-mesh-state.md && git commit`. |
| 7 (notify) | Failsoft — manual ping is fine. |
| 8 (drop-in hook) | Check stderr; re-run individual hook with env vars exported. |

## Configuration

| Flag / env | Default | Purpose |
|------------|---------|---------|
| `--instance-file` / `OCI_INSTANCE_FILE` | `~/.cloudprovider/oci-instance.json` | input from lottery daemon |
| `--dns-name` / `OCI_DNS_NAME` | `oci-1.kooshapari.com` | DNS A record |
| `--cf-zone-id` / `CF_ZONE_ID` | `6c9edab581e9c7b8fdb6a83adc6878ea` | kooshapari.com zone |
| `--cf-token-file` / `CF_TOKEN_FILE` | `~/.cloudflare-token` | Cloudflare API token |
| `--repo` / `PHENOTYPE_INFRA_REPO` | `~/CodeProjects/Phenotype/repos/phenotype-infra` | target repo for mesh commit |
| `--playbook` | `iac/ansible/playbooks/oci-baseline.yml` | ansible playbook (relative to repo) |
| `--hooks-dir` / `OCI_HOOKS_DIR` | `~/.config/phenotype/oci-acquire-hooks.d` | drop-in hook directory |
| `--dry-run` | off | runs steps 1-4 only; skips DNS/commit/notify/hooks |
| `TS_API_KEY` | (required for step 3) | Tailscale API key |
| `TS_TAILNET` | (required for step 3) | Tailscale tailnet name |

## Layout

```
iac/oci-post-acquire/
├── Cargo.toml                       # sibling crate to oci-lottery
├── src/
│   ├── main.rs                      # orchestrator + steps 1, 2, 4, 7
│   ├── tailscale.rs                 # step 3
│   ├── cf.rs                        # step 5
│   ├── mesh.rs                      # step 6
│   └── hooks.rs                     # step 8
├── oci-post-acquire.sh              # 5-line bash wrapper for ~/.local/bin/
└── hooks.d.example/
    ├── README.md
    └── 10-update-portfolio-card.sh
```

## Security notes

- Cloudflare token is read from a file (`~/.cloudflare-token`), never from CLI args (avoid `ps`-leak).
- Tailscale auth-keys are ephemeral + single-use + 10-min TTL.
- SSH is `accept-new` for the first connect (instance is brand-new, no host key pin yet); the Ansible baseline pins host keys via known_hosts on subsequent runs.
- All persisted artifacts (mesh state commit, worklog, drop-in JSON edits) flow through git — auditable.

## Open follow-ups

- Wire `oci-lottery` (sibling crate, branch `feat/oci-lottery-daemon`) to invoke `oci-post-acquire.sh` on success.
- Add a `--reconcile` mode that runs only the idempotent steps for an already-bootstrapped node.
- Consider pinning SSH host keys via Tailscale's `tailscale ssh` once step 3 lands, to remove `accept-new`.
