# Vendored cross-cutting crates (G2 chokepoint repoint)

Temporary path dependencies for crates migrating from HexaKit to phenoShared per
[DOMAIN_ROLES](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/rationalization/DOMAIN_ROLES.md).

| Crate | Source | Target |
| --- | --- | --- |
| `phenotype-errors` | HexaKit `crates/phenotype-errors` | phenoShared (Wave E) |
| `phenotype-event-bus` | HexaKit `crates/phenotype-event-bus` | phenoShared (Wave E) |

`phenotype-error-core` is already consumed from `<REDACTED>/phenoShared` git.

Remove this directory once phenoShared publishes both crates on `main`.
