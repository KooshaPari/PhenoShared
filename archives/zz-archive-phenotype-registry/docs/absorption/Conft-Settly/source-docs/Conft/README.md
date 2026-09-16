> **Work-state:** ARCHIVED
>
> Conft has been drained into [KooshaPari/Configra](https://github.com/KooshaPari/Configra)
> and is now archived. See ADR-031 / L5-111.
>
> All unique content has been absorbed:
> - `crates/pheno-config/` → already in Configra as canonical v0.2.0
> - `crates/config-schema/` → adapted and moved to Configra (`crates/config-schema/`)
> - `typescript/packages/conft/` (`@phenotype/config-ts`) → moved to Configra (`typescript/packages/conft/`)
>
> No further development will happen in this repo.

# Conft (ARCHIVED)

**Status:** ARCHIVED

**Universal Configuration Management with Cross-Language Support**

This repository is archived. All content has been migrated to
[**KooshaPari/Configra**](https://github.com/KooshaPari/Configra).

## Migration

| Content | New home |
|---------|----------|
| Rust `pheno-config` crate | [`Configra/crates/pheno-config`](https://github.com/KooshaPari/Configra/tree/main/crates/pheno-config) |
| Rust `config-schema` crate | [`Configra/crates/config-schema`](https://github.com/KooshaPari/Configra/tree/main/crates/config-schema) |
| `@phenotype/config-ts` (TypeScript) | [`Configra/typescript/packages/conft`](https://github.com/KooshaPari/Configra/tree/main/typescript/packages/conft) |
| Docs, ADRs, governance | [Configra](https://github.com/KooshaPari/Configra) |

## License

MIT OR Apache-2.0
