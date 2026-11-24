# template-lang-swift

Swift language layer templates composed on top of template-commons.

## Layer Contract

- layer_type: language
- layer_name: template-lang-swift
- versioning: semver

## Usage

1. Install `task` and the `swift` toolchain for your target platform.
2. Run `task check` to validate contracts and docs before release.
3. Use `swift build --package-path templates/swift` to verify the generated package.

## Validation / Smoke Checks

- `task quality` validates manifests, docs, and scaffold smoke tests.
- `scripts/scaffold-smoke.sh` now asserts docs, manifest content, and runs `swift package dump-package`.

## Generated Files

- `templates/swift/Package.swift`
- `templates/swift/Sources/App/main.swift`
- `templates/swift/Tests/Unit/UnitTests.swift`
- `templates/swift/Tests/Integration/IntegrationTests.swift`

## Docs

- [docs/index.md](docs/index.md)
- [docs/UPGRADE.md](docs/UPGRADE.md)
- [docs/BRANCH_PROTECTION.md](docs/BRANCH_PROTECTION.md)

## Localization

This layer ships English-only docs/test scaffolds. Localization must be added by downstream adopters.
