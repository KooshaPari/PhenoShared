# Contributing to phenotype-router-spec

Thank you for your interest in the Phenotype router protocol spec!

## Scope

This repo is the **canonical specification** for the phenotype router A2A wire protocol.
It contains 4 JSON Schemas, 4 prose docs, and worked examples — not implementation code.

For runtime implementation changes, see:
- [`KooshaPari/substrate`](https://github.com/KooshaPari/substrate) — Rust reference implementation
- [`KooshaPari/substrate-adapters-bundle`](https://github.com/KooshaPari/substrate-adapters-bundle) — adapter crates

## How to contribute

1. **Open an issue first** — discuss the change before opening a PR, especially for
   breaking protocol changes.
2. **Keep changes scoped** — one PR per logical change (schema update, doc fix, new example).
3. **Update all artifacts** — if you change a JSON Schema, update the matching prose doc
   and any affected examples so they stay in sync.
4. **Validate schemas** — ensure your JSON Schema changes are valid by running
   `npm run validate` (or the equivalent schema validator of your choice).

## PR guidelines

- PR titles follow [conventional commits](https://www.conventionalcommits.org/):
  `feat:`, `fix:`, `docs:`, `schema:`, `chore:`.
- Describe *what* changed and *why* (the motivation, not just the diff).
- Link to the related issue.

## Code of conduct

Be respectful, constructive, and assume good faith. This is a small spec project —
every contribution is appreciated.
