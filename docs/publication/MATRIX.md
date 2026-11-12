# Publication Matrix

Generated: 2026-11-12
Branch: `docs/p5-p8-roadmap`
Machine-readable register: `sdk-catalog.json` (290 members, 50 `publish`, 240 `internal`, 0 `quarantine`)

## What this document is

`sdk-catalog.json` records, per crate, which publication class it belongs to. It does
not record whether the publication path for that class works. This matrix is the second
half: for each distribution channel, what the artifacts are, what mechanism ships them,
what would fail if they were wrong, and the state as measured.

Every count below was produced by a command on this branch. Where a value could not be
measured, the cell says `UNKNOWN` rather than a plausible number.

## Channel matrix

| Channel | Artifacts | Mechanism | Fail-closed check | State | Evidence |
|---|---|---|---|---|---|
| crates.io | 50 publish crates | `release-plz.toml` + `.github/workflows/release-crates.yml` (tag `v*` or manual, batches of up to 10) | `sdk-catalog.json` publication class; `cargo deny check` (licenses) | Credential-gated, never exercised | `release-crates.yml:3-18`; needs `CARGO_REGISTRY_TOKEN` |
| Python | 82 `pyproject.toml` | No workflow found for PyPI | none | UNKNOWN | `git ls-files` |
| npm | 163 `package.json` | `.github/workflows/release-npm.yml` | none | Credential-gated, never exercised | `git ls-files`; workflow present |
| Go modules | 47 `go.mod` | No publish workflow found | `go-modules` job verifies every `go.mod` is declared or excluded (advisory in `ci / lint`) | Declaration gate only | `.github/workflows/ci.yml` `go-modules` job |
| Binary / desktop | per-crate `[[bin]]` | `release-binary.yml`, `release-attest.yml`, `release-attestation.yml` | sigstore attestation workflow present | UNKNOWN (no release ever run) | workflow files present |
| Docs site | VitePress tree | `.github/workflows/docs.yml` via `bun run build` | `bun run build` | UNKNOWN | `package.json` scripts |
| Landing packages | — | `release-landing-packages.yml` | none | UNKNOWN | workflow present |
| promptscrape | tagged releases | `release-promptscrape.yml` | none | Partially exercised | tags `promptscrape-v0.1.0/1/2` exist |

## Versioning

`[workspace.package]` in the root `Cargo.toml` sets `version = "0.3.10"`,
`edition = "2021"`, `rust-version = "1.80"`, `license = "MIT OR Apache-2.0"`,
`repository`, and `publish = false`.

Because the workspace default is `publish = false`, a crate only publishes by
overriding `publish` locally. The 50 publish crates do override it.

Within that set:

| Property | Inherited from workspace | Declared locally |
|---|---|---|
| `version` | 28 | 22 |
| `rust-version` | 46 | 4 |

The 4 local `rust-version` values are `1.75` (`nvms-manifest`, `pheno-otel`,
`pheno-tracing`) and `1.81` (`fabric-capability`).

The 22 local versions are not a single value: they span `0.0.1`, `0.1.0`,
`0.1.0-alpha`, `0.2.0`, `0.3.10`, `0.4.0-pre.0`, and `0.8.0`. That is the substantive
publication risk in this repo: `release-plz` bumps the workspace version and cannot
compute a coherent next version for 22 crates whose versions are independent and in
several cases lower than the workspace. Two of them are pre-release and one is
`0.0.1`, which crates.io treats as permanently unstable.

Deciding per-crate versions is a product decision, so this document records the
distribution and does not change it.

## Tags

9 tags exist, of which 4 are release tags:

- `v0.2.0`
- `promptscrape-v0.1.0`, `promptscrape-v0.1.1`, `promptscrape-v0.1.2`

The other 5 are `archive/*` worktree-retirement markers.

The workspace is at `0.3.10` and no tag names `0.3.10`. So the current version has
never been tagged, which means `release-crates.yml` (tag-triggered) has never fired
for it.

## Changelogs

25 of 290 members carry a checked-in per-crate `CHANGELOG.md`
(`git ls-files | grep -cE '^crates/[^/]+/CHANGELOG.md$'`). `release-plz.toml` sets
`changelog_update = true` with `changelog_config = "cliff.toml"`, so release-plz
generates changelogs at release time. The checked-in set is a partial backfill, not
the source of truth.

## Fixed in this pass

22 publish crates declared no `rust-version` at all. Their MSRV was unspecified, which
is a real defect for a published crate: a consumer on an older toolchain gets a
confusing compile failure rather than a resolver error. Each now declares
`rust-version.workspace = true`, inheriting `1.80`:

`eyetracker-camera`, `eyetracker-domain`, `model-plan`, `native-abi`,
`turbo-quant-mojo`, `pheno-errors`, `pheno-flags`, `pheno-vcs-core`,
`phenotype-error-core`, `phenotype-gfx`, `phenotype-health`, `phenotype-mcp`,
`phenotype-tooling-observability`, `phenovcs-observability`, `pine-core`,
`sharecli-fleet`, `sharecli-fuse`, `sharecli-mesh`, `sharecli-session`,
`sharecli-sync`, `spawn-core-sys`, `teamcomm-protocol`.

Verified after the change: all 50 publish manifests parse as TOML, and 0 declare no
`rust-version`.

## Remaining blockers, in order

1. **Heterogeneous crate versions.** 22 publish crates version independently of the
   workspace. `release-plz` cannot produce a coherent release train until this is
   decided. Product decision required.
2. **No tag for the current version.** `0.3.10` is untagged, so the tag-triggered
   batch publisher has never run for it. Tagging is a release action, not a fix.
3. **Publication credentials are absent.** `release-crates.yml` needs
   `CARGO_REGISTRY_TOKEN`; `release-npm.yml` needs an npm token. Neither has been
   exercised, so the workflows are unproven rather than known-good. `UNKNOWN`, not
   `PASS`.
4. **Python has no publish path at all.** 82 `pyproject.toml` files and no workflow
   that builds or uploads them.
5. **Changelog backfill.** 25 per-crate changelogs for 290 members; release-plz covers
   the gap at release time but no historical changelog exists for the other 265.

## Reproduction

```bash
python3 - <<'PY'
import json,os,re
d=json.load(open("sdk-catalog.json"))
print(len(d["members"]), len([m for m in d["members"] if m["publication_class"]=="publish"]))
PY
git ls-files | grep -c 'pyproject.toml$'
git ls-files | grep -c 'go.mod$'
git ls-files | grep -c 'package.json$'
git ls-files | grep -cE '^crates/[^/]+/CHANGELOG.md$'
git tag --list
```
