# release-cut

Standalone Rust binary orchestrating end-to-end TestFlight releases for FocalPoint.

## Subcommands

### `release-cut v0.0.7 [--execute]`

Dry-run plan (default) or execute full release:

1. **Git tag:** Create annotated tag `v0.0.7`
2. **Version bumps:** Update `Cargo.toml` and `apps/ios/.../Info.plist`
3. **CHANGELOG:** Prepend release section from `focus release-notes`
4. **Discord announcement:** Post to #releases webhook with categorized embeds
5. **Fastlane beta:** Invoke `fastlane ios beta version:0.0.7` to build and upload TestFlight

**Dry-run** (default):
```bash
release-cut v0.0.7
```

**Execute**:
```bash
release-cut v0.0.7 --execute
```

### `release-cut rollback v0.0.7`

Revert the release: delete git tag, reset version bumps, preserve CHANGELOG.

```bash
release-cut rollback v0.0.7
```

## Lanes

| Lane | Invocation | Purpose |
|------|-----------|---------|
| `fastlane ios beta` | `fastlane ios beta version:0.0.7` | Increment build number, sign, upload to TestFlight, notify testers |

## Environment

| Variable | Purpose | Optional? |
|----------|---------|-----------|
| `FOCALPOINT_DISCORD_WEBHOOK` | Discord #releases webhook URL | Yes (skips post if unset) |
| `GITHUB_TOKEN` | GitHub API (for release creation) | Yes (dry-run only) |

## Tests (4+)

- **FR-RELEASE-001:** Dry-run emits valid plan (structure + git tag format)
- **FR-RELEASE-002:** Version bump correct per semver (patch/minor/major)
- **FR-RELEASE-003:** Rollback reverts tag + bumps, preserves CHANGELOG
- **FR-RELEASE-004:** Discord post includes all commits since last tag

```bash
cargo test -p release-cut
```

## Usage

```bash
# From FocalPoint root:
cd /Users/kooshapari/CodeProjects/Phenotype/repos/FocalPoint

# Dry-run
cargo run -p release-cut -- v0.0.7

# Execute (with FOCALPOINT_DISCORD_WEBHOOK set in .env)
source .env
cargo run -p release-cut -- v0.0.7 --execute

# Rollback (if fastlane fails midway)
cargo run -p release-cut -- rollback v0.0.7
```

## Integration with `task release`

See `Taskfile.yml`:

```bash
task release:dry    # release-cut v0.0.X (prompts for version)
task release:cut    # release-cut v0.0.X --execute
```

## Failure Recovery

If fastlane fails during the build step:

1. Review fastlane output (often cert/provisioning issues)
2. Fix (re-run cert ceremonies, update provisioning profiles)
3. Rollback: `release-cut rollback v0.0.7`
4. Retry: `release-cut v0.0.7 --execute`

All changes are reversible except CHANGELOG (intentional; documents the attempt).
