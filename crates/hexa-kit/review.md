# review.md — Kilo Code Stand (HexaKit)

## Kilo Code Stand

- **standard_id:** `kilo-code-stand@1`
- **applies_to:** all PRs
- **owner:** <REDACTED>
- **charter:** [charter.md](charter.md)
- **sota:** [SOTA.md](SOTA.md)

## HexaKit-specific rules

| Tier | Rule |
|------|------|
| **Block** | New domain SDK crate without charter amendment |
| **Block** | Template change without updating `docs/genesis/` spec if format changes |
| **Block** | Removing genesis scaffold files from `templates/genesis/` without migration path |
| **Warn** | `crates/` growth — suggest `phenotype-rust-sdk` instead |
| **Warn** | OKF manifest not updated when genesis docs change |

## Test policy

| Change | Evidence |
|--------|----------|
| Template edit | `scripts/scaffold-smoke.sh` or language-specific smoke |
| Genesis doc | OKF validate (planned); link check in PR |
| Compliance scanner schema | `cargo test -p phenotype-compliance-scanner` |

## Agent roster

See [docs/genesis/REVIEW_SPEC.md](docs/genesis/REVIEW_SPEC.md). HexaKit PRs must pass:

- CI workflows on `templates/`
- No `cargo build` requirement for doc-only PRs

## Output format

Standard Kilo Review Summary per [templates/genesis/review.md](templates/genesis/review.md).
