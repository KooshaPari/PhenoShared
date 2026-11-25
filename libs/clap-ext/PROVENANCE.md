# Provenance

This repository was reconstructed on 2026-11-17. It is not a recovered git history: it is a
rebuilt tree, and every file in it came from one of two identified sources.

## Why it exists

`clap-ext` 0.1.0 is published on crates.io. Its crate metadata declares

    repository = "https://github.com/KooshaPari/clap-ext"

and that URL returned **HTTP 404** when checked on 2026-11-17. A published crate pointing at a
missing repository means the source-of-record for a public artifact did not exist on any reachable
host. This repository restores it.

## Source A - the published crate (authoritative for code)

`https://static.crates.io/crates/clap-ext/clap-ext-0.1.0.crate` (15,981 bytes, `gzip`), fetched
2026-11-17. It contributes:

| File | SHA-256 (first 16) |
|---|---|
| `Cargo.toml` | `565da1da278f0088` |
| `Cargo.lock` | from the `.crate` |
| `src/*.rs` (6 files) | `src/lib.rs` = `e7707ab9116fbade` |
| `tests/{common_args,common_subcommands,error,integration}.rs` | `tests/common_args.rs` = `4b32027cc58266` |

The `.crate` also carries `Cargo.toml.orig`, the workspace-inheriting manifest as authored
(`version.workspace = true`, `clap = { workspace = true }`). It is preserved verbatim at
`docs/provenance/Cargo.toml.authored`. The `Cargo.toml` in this repository root is the
**publish-normalized** manifest that crates.io actually shipped, because that is the one that is
known to resolve and build standalone. The workspace root that supplied `[workspace.package]`
values is **not recoverable**, so it is not reconstructed.

Publish provenance recorded by cargo itself:

```json
{"git": {"sha1": "35c3f0783dbb70fc1857303429165e45ca5b4188"}, "path_in_vcs": "crates/clap-ext"}
```

`path_in_vcs` is `crates/clap-ext`, so 0.1.0 was published out of a **monorepo** path, even though
the manifest advertised a standalone repository. Published 2026-06-20T07:47:15Z, crate owner
`KooshaPari`, 44 downloads at the time of reconstruction.

## Source B - the archive branch (metadata and docs)

`KooshaPari/phenotype-archives-20261108` at `0bdd7bf`, paths `crates/clap-ext/**`. It contributes
the files the published `.crate` does not contain: `README.md`, `CHANGELOG.md`, `LICENSE`,
`LICENSE-APACHE`, `LICENSE-MIT`, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
`AGENTS.md`, `CLAUDE.md`, `.gitignore`, `docs/slsa.md`, `docs/specs/{FR,TRACEABILITY}.md`, and
`examples/basic/src/main.rs`.

## The two sources are different revisions, and this repo does not pretend otherwise

Source B is **not** 0.1.0. Comparing the six source files:

| File | published 0.1.0 | archive `0bdd7bf` |
|---|---|---|
| `clap_based_cli.rs` | `e0dc29d09f6abc3d` | `e0dc29d09f6abc3d` (match) |
| `logging.rs` | `9bd45503a9e3396d` | `9bd45503a9e3396d` (match) |
| `common_args.rs` | `e484e46369ecc539` | `b4be2fbe41ab90a1` |
| `common_subcommands.rs` | `4faeb25b6fcebb2d` | `bdab2cd44b8744b1` |
| `error.rs` | `689cec17fe08c8d3` | `78bce213040528dc` |
| `lib.rs` | `e7707ab9116fbade` | `0686844c0ad25ffc` |

The archive also has **zero test files**, while the published crate has four. So the archive
snapshot predates the test suite and diverges from the shipped revision. The archive revision is
preserved on the archive branch and is deliberately **not** reconcilable here: no commit graph
survives to say which came first, and inventing an interleaving would be fabrication.

Consequence for the `examples/basic` binary, which exists only in Source B: it belongs to the
archive revision and is kept because it is the only copy, not because it matches 0.1.0.

## What was excluded, and why

`tests/integration.rs` was moved verbatim to `attic/integration-workspace-coupled.rs`. It shells
out to `cargo run -q -p basic` with `current_dir` set to `manifest_dir/../..`, i.e. it requires a
**workspace root two levels above this crate** containing a separate package named `basic`. It is
workspace-coupled by construction and cannot pass in a standalone repository. Keeping it in
`tests/` would have made `cargo test` red for a reason that has nothing to do with the library.

The remaining 29 tests pass:

    cargo test --lib --test common_args --test common_subcommands --test error
    -> 18 + 4 + 3 + 4 = 29 passed, 0 failed

## What is still unknown

- The original repository root manifest, and therefore the real `[workspace.package]` block.
- Whether the archive revision is older or newer than 0.1.0 (no surviving commit graph).
- Whether `examples/basic` was ever part of the published crate; the `.crate` strips examples.
- The commit `35c3f078...` itself, which lived in a repository that no longer exists.
