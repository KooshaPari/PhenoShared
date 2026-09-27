# oci-acquire-hooks.d (drop-ins)

Install dir: `~/.config/phenotype/oci-acquire-hooks.d/`

Every executable file here is run lexicographically by `oci-post-acquire` after
the core chain succeeds. Hooks receive instance metadata via env vars:

| Env var | Description |
|---------|-------------|
| `OCI_INSTANCE_OCID` | OCID of the new instance |
| `OCI_REGION` | OCI region |
| `OCI_AD` | Availability domain |
| `OCI_PUBLIC_IP` | Public IPv4 |
| `OCI_ACQUIRED_AT` | RFC3339 timestamp |

Conventions:

- Numeric prefix (`10-`, `20-`, …) controls order.
- Each hook MUST be idempotent; the chain may be re-run on partial failure.
- Hooks SHOULD exit non-zero only on real errors — warnings via stderr.
- Per Phenotype scripting policy, prefer Rust/Go binaries; bash hooks are
  permitted only as ≤5-line glue with an inline justification comment.

## Bundled example

`10-update-portfolio-card.sh` — flips `mesh: ✅` for the OCI node in
`projects-landing/data/repos.json`.
