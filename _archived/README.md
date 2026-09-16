# Archived Duplicate Crates

Per REP-080 and ADR-015, these crates duplicated code from canonical repos
and have been archived. phenotype-infra scope is now IaC + shared infra only.

| Archived Crate | Canonical Repo | Reason |
|---------------|----------------|--------|
| `nanovms-core/` | [nanovms](https://github.com/<REDACTED>/nanovms) | Go runtime — canonical source of truth |
| `nvms-ffi/` | [PhenoCompose](https://github.com/<REDACTED>/PhenoCompose) | Rust FFI bindings — canonical in PhenoCompose |
| `pheno-compose/` | [PhenoCompose](https://github.com/<REDACTED>/PhenoCompose) | Rust driver — born unified with nanovms |
| `byteport/` | [BytePort](https://github.com/<REDACTED>/BytePort) | Infra tooling — canonical in BytePort repo |

**Do not add new code here.** These are preserved for historical reference only.
