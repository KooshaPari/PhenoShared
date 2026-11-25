# Upgrade Guide

## Rules

1. Bump `contracts/template.manifest.json` version for any behavior change.
2. Keep reconcile behavior backward-safe for `smart` mode.
3. Document any new owned/protected paths.

## Validation

Run:

```bash
task check
```
