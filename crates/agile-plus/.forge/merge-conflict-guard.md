# AI-DD Crutch: Merge Conflict Marker Guard

## Rule: `merge_conflict_markers`

### Severity
FAIL (blocks commit)

### Trigger
Any source file (`.rs`, `.toml`, `.yml`, `.md`, `.json`, `.js`, `.ts`) is
staged and contains unresolved merge conflict markers:

- `<<<<<<< HEAD`
- `=======`
- `>>>>>>> branch-name`

### Rationale

Merge conflict markers left in source files cause compilation failures and
runtime errors. They must be resolved before commit.

### Exemptions

- Test fixtures that intentionally include conflict markers (must be in
  `tests/fixtures/` or `testdata/`)
- Documentation files explaining merge conflict resolution

### Verification

```bash
pheno-vibecoding-guard run --check merge_conflict_markers
```
