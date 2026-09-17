# pheno-context

Request context propagation for the pheno-* fleet (L37): trace/span/request IDs,
user/org metadata, extensible key-value bag.

## Status: ABSORBED into `pheno` workspace

This crate was absorbed from <https://github.com/KooshaPari/pheno-context>
on **2026-08-14** per docket `plans/dockets/N15-pheno-substrate-family.md`.

## Usage

```rust
use pheno_context::{Context, ContextBuilder};

let ctx = ContextBuilder::new()
    .request_id("req-123")
    .user_id("u-42")
    .org_id("o-7")
    .build()
    .unwrap();

assert_eq!(ctx.request_id(), "req-123");
```

## Features

- `oidc` — enables OIDC claims validation (`src/oidc.rs`)

See `CHANGELOG.md` for version history.