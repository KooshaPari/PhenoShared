# Hexagonal Rust Template

<!-- Migrated from KooshaPari/Apisync (archived 2026-06-19) — original commit d981353 -->

This template was extracted from [`KooshaPari/Apisync`](https://github.com/KooshaPari/Apisync)
shortly before that repository was archived on 2026-06-19. It preserves the **hexagonal /
ports-and-adapters** scaffold patterns that Apisync used: a thin `Taskfile`-driven quality
gate, a tightly-pinned Rust toolchain, opinionated lint/format/audit configs, and a starter
Sentry module that integrates cleanly into an API service.

## Origin

| Field            | Value                                                             |
| ---------------- | ----------------------------------------------------------------- |
| Source repo      | `KooshaPari/Apisync` (archived 2026-06-19)                        |
| Source commit    | `d981353` — *"wip: pre-push snapshot 2026-06-18T02:00:13Z"*       |
| Reason           | Apisync deprecated per ADR-017; template absorbed here for reuse  |
| License          | Apache-2.0 (inherited from Apisync)                               |

## What you get

```
templates/hexagonal/
├── README.md                        # this file
├── Taskfile.yml                     # build / test / lint / audit / bench / clean / default
├── mise.toml                        # mise task aliases (format, lint, test, build, audit, docs)
├── rust-toolchain.toml              # pins nightly + rustfmt, clippy, rust-docs
├── rustfmt.toml                     # Phenotype formatting standard (100-col, grouped imports)
├── nextest.toml                     # cargo-nextest profile with per-test/per-item timeouts
├── _typos.toml                      # typos-cli wordlist + exclude globs
├── deny.toml                        # cargo-deny license allowlist + RUSTSEC advisories
├── .clippy.toml                     # clippy cognitive-complexity + lint relaxations
├── cliff.toml                       # git-cliff conventional-commits changelog config
├── src/
│   └── sentry_config.rs             # starter sentry init + API error capture helpers
└── .agileplus/
    └── specs/
        └── 001-core-setup/          # core-setup spec scaffolding (Apisync FR-APISYNC-SENTRY-001)
            ├── spec.md
            ├── tasks.md
            └── meta.json
```

## How to consume this template

### 1. Copy into a new crate

```bash
# From the new crate root
cp -r /path/to/pheno-cargo-template/templates/hexagonal/. .
```

### 2. Customize the placeholder values

- **`Taskfile.yml`** — replace `PROJECT: apisync` with your crate name in the `vars` block.
- **`rust-toolchain.toml`** — keep `nightly` unless you have a strong reason to drop it; Apisync
  relied on nightly-only formatter behaviour.
- **`deny.toml`** — the RUSTSEC advisories ignored in this file are Apisync-specific
  (`rustls-pemfile`, `gix`, `async-nats`). Re-evaluate them for your dependency tree.
- **`cliff.toml`** — the conventional-commit group names are inherited as-is.
- **`sentry_config.rs`** — the trace tag `FR-APISYNC-SENTRY-001` should be replaced with your
  feature ID; the helpers themselves (`init`, `capture_api_error`, `set_request_context`)
  are domain-agnostic.

### 3. Wire up Sentry (optional)

```rust
// src/main.rs
mod sentry_config;

fn main() {
    let _guard = sentry_config::init();
    // ...
}
```

Add to `Cargo.toml`:

```toml
[dependencies]
sentry = "0.34"
```

### 4. Run the quality gate

```bash
task              # full gate: build + lint + test
task build
task test
task lint         # clippy -D warnings + fmt --check
task audit        # cargo audit
task bench
```

Or via `mise`:

```bash
mise run build
mise run lint
mise run test
mise run audit
```

## Customization notes

- The `_typos.toml` `extend-words` block (`agileplus`, `RTO`, `unparseable`) is from the
  Phenotype monorepo. Trim or extend it for your vocabulary.
- `rustfmt.toml` enforces 100-column wrapping (`max_width = 100`) per the Phenotype standard.
- The `.agileplus/specs/001-core-setup/` tree is **starter scaffolding** — replace the spec
  content with your own feature once you fork the template. The `meta.json` carries a
  `_attribution` field recording the original commit; remove it once you've forked.

## See also

- [`KooshaPari/Apisync`](https://github.com/KooshaPari/Apisync) @ `d981353` — the source of truth
- [`KooshaPari/pheno-cargo-template`](../..) — this repository's root
- ADR-017 — *"Deprecate Apisync; absorb template patterns into pheno-cargo-template"*