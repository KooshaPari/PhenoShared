# Migration: pheno-agents -> Pyron

**Date:** 2026-06-17
**Disposition:** Wave F python redirect stub
**Canonical repo:** https://github.com/KooshaPari/Pyron

## What changed

- Implementation ownership moves to **Pyron**.
- This HexaKit path is a **pointer stub** until downstream references are cleared.

## For consumers

1. Install from Pyron canonical repo, not HexaKit python/pheno-agents.
2. Registry row: disposition-index **py-pheno-agents**.

## For HexaKit maintainers

- Remove this directory after repoint PRs merge (follow-up).
