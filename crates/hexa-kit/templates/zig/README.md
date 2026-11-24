# template-lang-zig

Zig language layer templates composed on top of template-commons.

## Layer Contract

- layer_type: language
- layer_name: template-lang-zig
- versioning: semver

## Usage

1. Install `task` and `zig` on your machine.
2. Run `task check` before releasing to verify manifests, docs, and scaffolds.
3. When Zig is available, run `zig build --build-file templates/zig/build.zig`.

## Validation / Smoke Checks

- `task quality` validates manifest files and runs `scripts/scaffold-smoke.sh`.
- `scripts/scaffold-smoke.sh` now asserts docs exist and optionally runs `zig fmt --check` plus `zig build`.

## Generated Files

- `templates/zig/build.zig` – entrypoint for generated projects.
- `contracts/template.manifest.json` – metadata the contract requires.
- `contracts/reconcile.rules.yaml` – ownership and reconcile directives.

## Docs

- [docs/index.md](docs/index.md) – landing page and overview.
- [docs/UPGRADE.md](docs/UPGRADE.md) – upgrade expectations.
- [docs/BRANCH_PROTECTION.md](docs/BRANCH_PROTECTION.md) – branch guard guidance.

## Localization

All docs and scaffolds are English-only; downstream layers must add localization assets if needed.
