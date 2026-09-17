# Git hooks (placeholder)

This directory was stamped by `hexakit init`. Canonical Phenotype hook bundles live in
[TestingKit](https://github.com/KooshaPari/TestingKit).

## Install

```bash
git config core.hooksPath .githooks
```

Replace the placeholder `pre-commit` and `pre-push` scripts with the TestingKit-published
versions when wiring production hooks.

## Bypass

- `HOOKS_SKIP=1 git commit` — skip all hooks
- `git commit --no-verify` — last resort
