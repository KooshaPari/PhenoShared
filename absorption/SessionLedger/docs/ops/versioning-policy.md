# Versioning & compatibility policy

Status: **C11 L119** — SemVer + Keep a Changelog cadence for desktop releases.

Related: [`CHANGELOG.md`](../../CHANGELOG.md), [`docs/ops/distribution.md`](distribution.md)
(versioning table), [`docs/reference/OKF-SPEC.md`](../reference/OKF-SPEC.md) §13.

## Rules

| Surface           | Policy                                                                                                    |
| ----------------- | --------------------------------------------------------------------------------------------------------- |
| Git tags / crates | SemVer `vMAJOR.MINOR.PATCH`; root `Cargo.toml` `version` matches the tag body before tagging              |
| CHANGELOG         | Keep a Changelog; every tagged release gets a `## [X.Y.Z] - YYYY-MM-DD` section (not only `[Unreleased]`) |
| rust-version      | Workspace `rust-version` (MSRV) is declared in root `Cargo.toml`; bump with a CHANGELOG note              |
| OKF documents     | Separate `[major].[minor]` rules in OKF-SPEC — independent of crate SemVer                                |

## Cadence

1. Accumulate notes under `[Unreleased]` during the wave.
2. On tag: move Unreleased bullets into a new `## [X.Y.Z] - <date>` section; leave an empty Unreleased stub.
3. Do not invent tagged sections for untagged commits.

## Machine verification

```powershell
pwsh ./scripts/versioning-policy-check.ps1 -SelfCheck
```
