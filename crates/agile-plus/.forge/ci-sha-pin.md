# AI-DD Crutch: CI Workflow SHA-Pin Guard

## Rule: `ci_workflow_sha_pin`

### Severity
FAIL (blocks commit)

### Trigger
A GitHub Actions workflow file uses an unpinned action reference such as:

- `@v1`
- `@v2`
- `@v3`
- `@main`
- `@master`

Instead of a SHA-pinned reference:

- `@a1b2c3d4e5f6...` (full SHA)

### Rationale

SHA-pinning prevents supply-chain attacks where a tag is moved to a
compromised commit. This is mandated by V3 §11 of the Phenotype security
baseline.

### Allowed patterns

| Bad | Good |
|-----|------|
| `actions/checkout@v4` | `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683` |
| `dtolnay/rust-toolchain@stable` | `dtolnay/rust-toolchain@56f84321dbaf38e9fdea393709281c1ba838bfa9` |

### Verification

```bash
pheno-vibecoding-guard run --check ci_workflow_sha_pin
```
