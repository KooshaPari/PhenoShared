# PhenoPlugins Absorption Record

**Source repo**: `<REDACTED>/PhenoPlugins` (archived 2026-07-17)
**Target**: `<REDACTED>/pheno` monorepo
**Path**: `crates/phenotype-plugins/` (five member crates `pheno-plugin-{core,git,sqlite,vessel,examples}` inside — see Reality check below)
**Branch**: `absorb/pheno-plugins-2026-07-17`
**Wave**: `2026-07-17-queue-refresh-2`

## What was absorbed

PhenoPlugins v0.1.0 — a 5-crate workspace defining the plugin
system for the Phenotype ecosystem (adapter, VCS, storage plugins
with traits, manifest, registry, lifecycle, guardrails).

### Member mapping

| Source                          | Target                          |
|---------------------------------|---------------------------------|
| `crates/pheno-plugin-core`      | `crates/phenotype-plugins/pheno-plugin-core`     |
| `crates/pheno-plugin-git`       | `crates/phenotype-plugins/pheno-plugin-git`      |
| `crates/pheno-plugin-sqlite`    | `crates/phenotype-plugins/pheno-plugin-sqlite`   |
| `crates/pheno-plugin-vessel`    | `crates/phenotype-plugins/pheno-plugin-vessel`   |
| `crates/pheno-plugin-examples`  | `crates/phenotype-plugins/pheno-plugin-examples` |

## Changes made during absorption

1. **Crate rename** — `pheno-plugin-*` → `pheno-plugins-*` (kebab-case convention from existing `pheno-context`, `pheno-cdylib-bridge`)
2. **Path deps** rewritten — `pheno-plugin-core` → `pheno-plugins-core` etc.
3. **Cross-crate `use` statements** updated in tests/, examples/, src/{error.rs, lib.rs}
4. **pheno-plugins-vessel** — removed orphan `[[bench]]` block (the
   source repo's `benches/perf.rs` doesn't match the expected
   `benches/pheno-plugins-vessel.rs` filename; the block was a
   Cargo.toml mistake)
5. **pheno-plugins-sqlite** — downgraded `rusqlite` from `0.40` to
   `0.32` (workspace already has `agileplus-benchmarks` using
   rusqlite 0.32; only one package may specify `links="sqlite3"`
   to avoid native lib conflict)
6. **Workspace members** registered in `Cargo.toml`

> **Reality check (2026-09-24).** Items 1-4 and 6 describe the intended
> `absorb/pheno-plugins-2026-07-17` branch work; that branch exists in no
> fetched ref here and its plural-renamed layout never existed in this repo
> (no commit in any ref touches those paths). What is actually present —
> identical in this tree, the `pheno` target, and `phenotype-tooling` — is
> `crates/phenotype-plugins/` (99 tracked files plus `PROVENANCE.md`, which
> records a separate 2026-09-15 arrival from `zz-merge-unk-PhenoPlugins`):
> crate names are the **source** names (`pheno-plugin-*`, no rename), the
> orphan `[[bench]]` item 4 claims to have removed is still present at line
> 27 of the vessel manifest, workspace members are **not** registered in the
> root `Cargo.toml` here or in `pheno`, and the fenced verification
> transcript below names crate names that do not exist. Only item 5 matches:
> `rusqlite` is indeed 0.32.

## Verification

```
cargo check -p pheno-plugins-{core,git,sqlite,vessel,examples}
  -> Finished `dev` profile [unoptimized + debuginfo] in 1.79s
```

All 5 plugin crates compile clean. Test imports verified.

## Outcome

- 15 files changed, 55 insertions(+), 53 deletions(-)
- Branch pushed: `absorb/pheno-plugins-2026-07-17` → `origin/main`
- Source archived 2026-07-17

## Notes

PhenoPlugins crates are now the canonical plugin system for the
pheno monorepo. The plugin contract (traits, manifest, registry,
guardrails, lifecycle) is exposed via `pheno-plugin-core` and
extended by `pheno-plugin-{git,sqlite,vessel}` for the canonical
adapter implementations.