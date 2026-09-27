# Runner Routing Specification

Normative label taxonomy and routing algorithm for Woodpecker CI agents across the 7-node mesh.

## Label taxonomy

Labels are declared at agent registration (`.woodpecker/agent.env`) and matched against `runs-on:` in pipelines.

| Label set | Node(s) | Purpose |
|-----------|---------|---------|
| `[self-hosted, oci, light]` | oci-primary, oci-secondary | Lint, fmt, docs, quick-check jobs |
| `[self-hosted, oci, medium]` | oci-secondary, gcp-e2 | `cargo test`, small builds |
| `[self-hosted, heavy, home]` | home-mac | `cargo build --release`, VRAM jobs, long integration |
| `[self-hosted, burst, hetzner]` | hetzner-burst (Phase 2) | Spillover when heavy queue depth > 3 |
| `[self-hosted, webhook]` | aws-lambda (virtual) | Webhook fanout jobs (reserved) |

## Routing algorithm

Woodpecker uses exact label-set match. Declaring `runs-on: [self-hosted, heavy, home]` matches any agent advertising **all three** labels. To enable fallback routing when `home-mac` is paused (Parsec, ADR 0008):

1. Jobs declare a **primary** label set and an **optional** `fallback:` block.
2. A small shim (Rust, `iac/scripts/queue-warden/`) polls Woodpecker for jobs queued > 10 min on `heavy,home` with no eligible agent and rewrites their label set to `burst,hetzner` (Phase 2).

## Concurrency budgets

| Label set | Max concurrent jobs |
|-----------|---------------------|
| `oci, light` | 8 per agent |
| `oci, medium` | 2 per agent |
| `heavy, home` | 1 |
| `burst, hetzner` | 2 |

## Declaration examples

```yaml
# Light job
steps:
  lint:
    image: rust:1.80
    commands: [cargo fmt --check, cargo clippy -- -D warnings]
    runs-on: [self-hosted, oci, light]

# Heavy job
steps:
  release:
    image: rust:1.80
    commands: [cargo build --release --workspace]
    runs-on: [self-hosted, heavy, home]
    fallback:
      runs-on: [self-hosted, burst, hetzner]
      timeout: 600  # rewrite after 10 min queue
```

## Governance

- Adding a new label requires ADR update (extend ADR 0007).
- Removing a label requires deprecation notice in this spec with migration deadline.
- Pipelines must not use bare `runs-on: self-hosted` (too ambiguous); CI guard rejects such declarations.

## Related

- ADR 0007, ADR 0003, `docs/runbooks/day1-home-runner-setup.md`
