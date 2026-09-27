# 2. Adopt a pinned nightly rustfmt for every formatting gate

Date: 2026-09-24

## Status

Accepted

## Context and Problem Statement

`rustfmt.toml` declares 29 options, 19 of which stable rustfmt refuses to set
(`brace_style`, `group_imports`, `imports_granularity`, `wrap_comments`,
`unstable_features`, … — full list in `docs/audits/FMT-GATE.md`). Measured
2026-09-19 and independent-verified 2026-09-19: stable `cargo fmt --all
-- --check` exits 1 wanting 288 distinct files; the same command under the
then-default nightly wants 456; the stable set is a strict subset (168
nightly-only, 0 stable-only), and under stable the config's effective effect
is *none* — byte-identical to no config at all.

The repository has three independent formatting scopes, each with its own CI
step:

| Scope | CI site | Gate strength |
|---|---|---|
| Root workspace | `ci.yml` → `cargo fmt --all -- --check` | advisory (`\|\| echo ::warning::`, job `continue-on-error`) |
| `iac/` | `iac-rust.yml` workspace job | **hard** (plain `run:`, workflow has no `continue-on-error`) |
| `iac/landing-bootstrap/` | `iac-rust.yml` landing-bootstrap job | **hard** |

All three CI steps ran **stable**, so the hard gates enforced exactly the
formatting stable can express and silently ignored the 19 options the config
asks for. Locally, `rust-toolchain.toml` pins the *build* toolchain to stable
while `rustup default` on the operator host is nightly, so a bare
`cargo fmt` produced different output depending on whether it was run inside
or outside the repository — the reproducibility trap recorded in
`docs/audits/FMT-GATE.md`.

## Decision

**Formatting is performed and gated exclusively by a pinned dated nightly:
`nightly-2026-07-31`. Builds, `cargo check`, clippy, and tests stay on the
stable channel pinned by `rust-toolchain.toml`.**

Concretely:

1. Every CI fmt step becomes `cargo +nightly-2026-07-31 fmt … --check`, with a
   preceding `rustup toolchain install nightly-2026-07-31 --profile minimal
   --component rustfmt --no-self-update` step in each job that needs it
   (`ci.yml` rust job, `iac-rust.yml` both jobs).
2. All three scopes are reformatted under that exact pin so each gate passes:
   root workspace, `iac/`, `iac/landing-bootstrap/`.
3. Gate *strengths* are unchanged by this decision: the root fmt step keeps its
   advisory `::warning::` swallow, and the two `iac-rust.yml` fmt steps stay
   hard. Hardening the root fmt gate into a blocking aggregate (and the same
   for the registry-invariant checker) is deliberate follow-on work, not part
   of this ADR.
4. The canonical local invocation is `cargo +nightly-2026-07-31 fmt`. A bare
   `cargo fmt` remains stable-formatted and therefore **wrong** for this
   repository; every instruction that mentions formatting must name the
   toolchain explicitly.

### Re-measured inputs (2026-09-24, under the pin)

| Scope | Toolchain | Distinct files | Hunks |
|---|---|---|---|
| Root workspace `--all` | `nightly-2026-07-31` | 496 | 2329 |
| Root workspace `--all` | stable | 309 | 1447 |
| `crates/phinbox` (`-p phinbox`) | `nightly-2026-07-31` | 81 | 466 |
| `iac/` | `nightly-2026-07-31` | 10 | 34 |
| `iac/landing-bootstrap/` | `nightly-2026-07-31` | 1 | 8 |

These differ from FMT-GATE's 2026-09-19 figures (456 files / 2184 hunks under
the then-*floating* nightly) because the tree changed in the intervening days
and the pin is a specific dated nightly rather than `nightly`. The pin is the
point: from this ADR onward the numbers above are reproducible by anyone who
installs `nightly-2026-07-31`.

Method note (repeated from FMT-GATE because it is easy to get wrong): a
`Diff in <absolute path>:<line>:` line is a **hunk**; distinct files require
stripping the `:<line>:` suffix before `sort -u`. Hunks ≠ files.

## Consequences

- Formatting becomes reproducible: same pin locally and in CI, dated, and
  bumpable only by an explicit edit to this ADR's pin (which also mandates a
  reformat pass, since rustfmt output drifts between nightlies).
- The root workspace reformat lands as message-scoped commits (phinbox first,
  remainder second) so review stays honest about scope.
- Stable-formatted contributions will now diff under CI's hard `iac` gates and
  warn under the root gate; the fix is always the pinned command above, never
  a config change.
- The two hard `iac` fmt gates are currently violated by the tree itself (10
  and 1 files respectively under the pin); this stack reformats them in the
  same push that installs the pin, so no red window is introduced.
- Deferred (explicitly out of scope): flipping the root fmt step from advisory
  to blocking, wiring `scripts/audit/registry-invariant.sh` into CI (WBS
  E10.7), and removing stable `rustfmt` from the developer loop entirely.
