# Contributing

Contributions are welcome. This is a Rust crate (see `Cargo.toml`). Read
`CLAUDE.md` first — it is the canonical contributor contract (project overview,
key commands, quality gates).

## Development setup

1. Fork and clone: `git clone https://github.com/<you>/DataKit.git`
2. Install the Rust toolchain:

   ```bash
   rustup toolchain install stable
   ```

3. Install the dev tools used by CI:

   ```bash
   cargo install cargo-nextest cargo-deny
   ```

## Verify commands (all verified working)

| Task | Command |
|---|---|
| Type-check | `cargo check` |
| Test | `cargo nextest run` (fallback: `cargo test`) |
| Lint | `cargo clippy --all-targets -- -D warnings` |
| Format | `cargo fmt --check` (check) / `cargo fmt` (apply) |
| Full gate (CI parity) | `cargo nextest run --all-features` with `RUSTFLAGS="-D warnings"` |

> Never run `cargo build --release` unless you need a distribution binary —
> debug builds are enough for development feedback.

## Code style

- Follow Rust idioms: `anyhow::Result` + `thiserror` errors, Rust docs (`///`)
  on all public items with `# Arguments`/`# Errors` sections.
- Tests live in the same file as the source or in `tests/`, using
  `pretty_assertions` and `fixture`/`actual`/`expected` naming.

## Submitting changes

1. Create a feature branch from `main`.
2. Make your changes; add or update tests and Rust docs.
3. Verify with the commands above.
4. Open a PR: summary, linked issue (if any), tests run, checklist (docs
   updated, no secrets, CI gates).
5. CI gates that must pass: `ci`, `lint`, `test`, `cargo-deny`
   (advisories + licenses + sources), `gitleaks`. Branch protection
   requires one approval and signed commits on `main`.

## Docs

- Capability changes update `README.md` and relevant source docs.
- Secrets: credentials are stored locally in `~/.datakit/credentials`
  (`0o600`, gitignored). Never commit credentials; use env vars or the local
  store.

## Questions

Open an issue for questions or discussions. Use the issue templates
(`.github/ISSUE_TEMPLATE/`) — feature requests, bug reports, and performance
reports have dedicated forms.
