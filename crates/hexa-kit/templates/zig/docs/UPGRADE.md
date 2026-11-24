# Upgrade Guide

## Rules

1. Bump the layer version whenever the Zig contract, generated scaffold, or manifest structure changes.
2. Maintain compatibility with the `template-commons` dependencies that back this layer.
3. Document any new files that the scaffold produces.

## Validation

Run the smoke path described in the README:

```bash
task check
zig build --build-file templates/zig/build.zig
```
