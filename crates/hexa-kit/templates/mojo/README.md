# template-lang-mojo

Mojo language layer templates composed on top of template-commons.

## Layer Contract

- layer_type: language
- layer_name: template-lang-mojo
- versioning: semver

## Usage

1. Install `task` and the Mojo CLI.
2. Run `task check` to validate contracts and docs.
3. When `mojo` is available, run `mojo run templates/mojo/main.mojo` inside the target scaffold to verify execution.

## Validation / Smoke Checks

- `task quality` checks manifests, docs, and the scaffold smoke script.
- `scripts/scaffold-smoke.sh` validates docs, inspects the manifest, ensures the Mojo file is well-formed, and optionally invokes `mojo --version`.

## Generated Files

- `templates/mojo/main.mojo`
- `contracts/template.manifest.json`
- `contracts/reconcile.rules.yaml`

## Docs

- [docs/index.md](docs/index.md)
- [docs/UPGRADE.md](docs/UPGRADE.md)
- [docs/BRANCH_PROTECTION.md](docs/BRANCH_PROTECTION.md)
- [contracts/README.md](contracts/README.md)

## Localization

Docs and scaffolds remain English-only; downstream adopters must add translations if needed.
