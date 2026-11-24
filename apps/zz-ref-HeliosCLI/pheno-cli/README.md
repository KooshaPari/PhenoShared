# pheno-cli

`pheno` is the org-wide release governance and developer experience CLI for Phenotype repositories. It automates publishing, promotion, auditing, and governance artifact bootstrapping across multiple package registries.

## Installation

```bash
go install github.com/KooshaPari/pheno-cli@latest
```

Or build from source:

```bash
git clone https://github.com/KooshaPari/pheno-cli
cd pheno-cli
go install ./...
```

## Usage

```bash
pheno --help
```

## Commands

- `pheno publish` - Publish packages to release channels (alpha, canary, beta, rc, prod)
- `pheno promote` - Promote releases between channels
- `pheno audit` - Audit release status and history
- `pheno matrix` - Generate release matrix across channels
- `pheno bootstrap` - Bootstrap governance artifacts for repositories
- `pheno config` - Manage CLI configuration

## Configuration

Configuration is stored at `~/.config/pheno/config.toml`. Environment variables with the `PHENO_` prefix override file-based configuration.

## Supported Registries

- npm (TypeScript/JavaScript)
- PyPI (Python)
- crates.io (Rust)
- Go modules
- Hex.pm (Elixir) — stub
- Zig — stub
- Mojo — stub

## License

MIT
