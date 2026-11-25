# Upgrade Guide

## Rules

1. Bump the layer version whenever generated Swift targets, manifests, or helper scripts change.
2. Keep the Swift scaffolding compatible with the `template-commons` baseline.
3. Cross-check docs and tests when adding new sources or assets.

## Validation

```bash
task check
swift package dump-package --package-path templates/swift
```
