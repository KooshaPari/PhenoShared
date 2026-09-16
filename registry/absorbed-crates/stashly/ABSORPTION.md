# Absorbed Crate: stashly (KooshaPari/Stashly)

## Source

| Field | Value |
| --- | --- |
| Source repo | KooshaPari/Stashly |
| Source size | 3138 LOC |
| Source branches | 14 |
| Source absorbed on | 2026-07-17 |
| Target | pheno monorepo `crates/stashly/` (federated — registry copy retained here for forensic) |

## Why absorbed

Stashly is a Rust hexagonal caching framework (TTL, multi-tier, singleflight,
CQRS-style r/w separation, memory/Redis/Memcached/disk backends). It formally
absorbs `thegent-cache` (per its README) and is a natural fit for the pheno
monorepo's caching layer. Filesystem retention here in the registry is for
forensic audit; the canonical target lives under portage.git federation
(refs/heads/source/... or direct pheno workspace member post-portage-handoff).

## Contents copied here

```
Cargo.toml       # crate name=stashly, v0.2.0
CHANGELOG.md
CLAUDE.md
AGENTS.md
ADR.md
src/             # adapters/, application/, domain/, infrastructure/, lib.rs,
                 # phenotype-cache-adapter/, ports/
benches/
```

2555 LOC of Rust.

## Verification

The crate is hexagonal with ports (Cache, CachePort) and adapter modules
(memory, Redis, Memcached, disk). Tests run via `cargo test -p stashly`
inside the pheno workspace.

## Notes

- Phase 1: registry forensic copy at `registry/absorbed-crates/stashly/`
- Phase 2: pheno monorepo workspace member + tests (portage-federation handoff)
- Phase 3: archive source `gh repo archive KooshaPari/Stashly -y`

Registry row: queue-repo-Stashly → absorbed (this commit).
