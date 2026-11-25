# Harbor install — pheno-harness ops guide

**Date:** 2026-08-11 (v0.13 Phase 7 task 92)

This guide covers installing Harbor 0.1.42 for use with pheno-harness
on macOS. Harbor is the **local development evidence store** that
`pheno-harness` ports as `phenotype-portage` for offline use.

## Prerequisites

- macOS 13+ (Tahoe tested on Apple Silicon; Intel also supported)
- Homebrew (`/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`)
- Python 3.12+ (already required by pheno-harness `.venv`)

## Install

```bash
# 1. Tap the harbor formula
brew tap phenoforge/harbor https://github.com/phenoforge/homebrew-harbor

# 2. Install harbor 0.1.42 (production-grade)
brew install phenoforge/harbor/harbor@0.1.42

# 3. Link it into PATH
brew link --force phenoforge/harbor/harbor@0.1.42

# 4. Verify
harbor --version
# expected: harbor v0.1.42 (rev: <commit>)

# 5. Start the local daemon
brew services start phenoforge/harbor/harbor@0.1.42

# 6. Health check
curl -fsS http://127.0.0.1:8290/health
# expected: {"status": "ok", "version": "0.1.42"}
```

## Smoke test

```bash
# 1. Run the harbor CI smoke test
.venv/bin/python -m pytest -q tests/test_portage_dev_store*.py

# 2. Verify pheno-harness can talk to harbor (round-trip)
.venv/bin/python -c "import urllib.request as u; \
  resp = u.urlopen('http://127.0.0.1:8290/health', timeout=3); \
  print(resp.read().decode())"
```

## Upgrade

```bash
brew upgrade phenoforge/harbor/harbor@0.1.42
brew services restart phenoforge/harbor/harbor@0.1.42
```

## Rollback

```bash
# Stop and pin to previous version
brew services stop phenoforge/harbor/harbor@0.1.42
brew switch phenoforge/harbor/harbor 0.1.41
brew services start phenoforge/harbor/harbor
```

## Cross-repo note

Harbor is consumed by:
- `phenotype-portage/` — local evidence store (the upstream home).
- `phenotype-omlx/` — uses harbor for model artifact transport.
- `pheno-harness/harbor_cli/` — PowerShell drivers (Windows path).

The `pheno-harness` Python sources never construct a Harbor client
directly; they consume `harbor://<host>/sha256/<digest>` URIs
through `phenotype-portage/sdk`.

Refs: v0.13-task-92, harbor-0.1.42.
