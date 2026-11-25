# Pheno dirty capture preservation manifest

This recovery snapshot preserves the dirty source state of `pheno` without
mutating the original checkout. It is based on parent commit
`be5da947c3fc747746b11f6f3010f9f15a7b21cb` from `<REDACTED>/pheno` `main`.

## Included

- All 14 tracked working-tree modifications present at capture time:
  `WORKLOG.md`, `audit/2026-07-21/inventory.json`,
  `audit/2026-07-22-omlx-cutover.md`, both device YAML files,
  `docs/GITHUB_ARCHIVE_POLICY.md`, three experiment YAML files,
  `promotion/gates.yaml`, both schema JSON files, `sync/manifest.json`, and
  `worklog.md`.
- Source-bearing, specification, documentation, configuration, and test files
  under `crates/agile-plus/` and `crates/hexa-kit/`.
- Captured payload size: approximately 69 MiB across 5,249 regular files
  under the two crates directories (5,263 staged paths including the 14
  tracked edits and this manifest).

## Explicit exclusions

The following local-only/generated payloads were excluded from this recovery
ref so the cloud ref contains reviewable source rather than rebuild output:

- Rust/Node build output: any `target/`, `node_modules/`, `dist/`, or `build/`
  directory, including nested copies.
- Local checkout metadata: any `.git/`, `*-wtrees/`, or `worktrees/`
  directory.
- Runtime/local state: `*.db`, `*.db-*`, `*.sqlite`, and `*.sqlite-*` files.
- Tool caches: `.cache/`, `.zig-cache/`, `.sccache` files, `.pytest_cache/`,
  `.mypy_cache/`, `.ruff_cache/`, `.vitepress/cache/`, `.tox/`, `.venv/`,
  and `coverage/`.
- Generated brand outputs: `assets/brand/generated/`.
- Compiled/intermediate files: `*.pyc`, `*.pyo`, `*.o`, `*.a`, `*.rlib`,
  `*.so`, and `*.dylib`.

Excluded paths remain in the original checkout and require a separate
evidence-backed capture if any are later shown to contain unique source or
history. No deletion, reset, clean, stash, or force-push was performed.
