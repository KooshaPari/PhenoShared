# Upgrade Guide

## Rules

1. Increase the `version` in `contracts/template.manifest.json` for any scaffold or contract change.
2. Keep `template-commons` dependencies aligned with this layer.
3. Document new assets added to the template.

## Validation

```bash
task check
mojo --version
```
