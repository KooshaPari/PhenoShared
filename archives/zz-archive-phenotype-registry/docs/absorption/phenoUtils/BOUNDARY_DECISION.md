# phenoUtils boundary decision

Date: 2026-06-20
Decision: `PRESERVE_ACTIVE_NARROWED`

`phenoUtils` remains active as the Rust primitive utility crate family. Its live crates are `pheno-crypto`, `pheno-fs`, `pheno-net`, `pheno-shell`, and `pheno-testing`.

PhenoLang primitive/support crates were preserved through `phenoUtils#68` under `archive/PhenoLang-primitives-2026-06-20`; that archive is traceability input, not a broadening of the active package boundary.

Do not delete `phenoUtils`. Do not add unrelated domain/framework/runtime crates here; use a tight substrate repo or SDK owner.
