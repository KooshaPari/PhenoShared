# Migration: pheno-atoms -> phenotype-types

**Date:** 2026-06-17
**Disposition:** Wave F python redirect stub
**Canonical repo:** https://github.com/KooshaPari/phenotype-types

## What changed

- Implementation ownership moves to **phenotype-types**.
- This HexaKit path is a **pointer stub** until downstream references are cleared.

## For consumers

1. Install from phenotype-types canonical repo, not HexaKit python/pheno-atoms.
2. Registry row: disposition-index **py-pheno-atoms**.

## For HexaKit maintainers

- Remove this directory after repoint PRs merge (follow-up).
