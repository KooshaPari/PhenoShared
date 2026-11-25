# AgilePlus in `helios-cli`

> One-page explainer. If you're new to the repo, read this first.

## What is AgilePlus here?

AgilePlus is the external delivery and quality tracker for this repository.
HeliosCLI does not carry an `agileplus/` directory, `kitty-specs/` tree, or a
copy of tracker worklogs. Those are tracker artifacts, not application source.

Every implementation branch, commit, and pull request cites one of:

| Identifier                | Use                                       |
| ------------------------- | ----------------------------------------- |
| `AP-ITEM:<id>`            | A queued external tracker item.           |
| `AP-FEATURE:<slug>/WP<n>` | An external feature and its work package. |

Create the item and record its scope and acceptance criteria in the external
AgilePlus service before implementation. When the service supports a lifecycle
transition, update the external item there. Do not use a local spec or a
checkout of the AgilePlus source repository as a substitute for tracker state.

## How a feature flows

```
idea → external AP-ITEM → scope and acceptance criteria in AgilePlus
     → HeliosCLI PR(s) citing the identifier → external tracker update
```

An external feature/work package records:

1. Requirements with `HCLI-FR-NNN-MMM` IDs.
2. Work packages (WP01, WP02, …).
3. Requirements-to-test matrix pointing at `tests/test_*.py`.
4. Acceptance criteria.

## Quality gates

Repository workflows and branch protection are the source of truth for what
blocks a PR. The external tracker records delivery scope and acceptance; it
does not replace repository CI, security, license, or documentation checks.

To run them locally:

```bash
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace --all-features --locked
cargo deny --workspace check advisories bans licenses sources
pnpm --filter docs build
```

## Where to start

1. Find or create the external `AP-ITEM` for the change.
2. Verify its scope and acceptance criteria before beginning implementation.
3. Cite the item in the HeliosCLI branch, commits, and pull request.
