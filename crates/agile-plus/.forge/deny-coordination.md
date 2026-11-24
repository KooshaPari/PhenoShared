# AI-DD Crutch: deny.toml Coordination Guard

## Rule: `gitignore_requires_deny_toml`

### Severity
ADVISORY (warns but does not block commit)

### Trigger
`.gitignore` is staged, but `deny.toml` is not also staged or already updated
to reflect the same rationale (e.g., adding a new crate to ignore should
match a deny.toml exception if applicable).

### Rationale

`.gitignore` and `deny.toml` are both supply-chain / ignore-policy files.
Changes to one should be reflected in the other to avoid silent policy drift.

### Required coordination

When `.gitignore` changes, the commit message or a linked issue must explain:
- Why the ignore was added
- Whether `deny.toml` also needs an exception or ban

### Verification

```bash
pheno-vibecoding-guard run --check gitignore_requires_deny_toml
```
