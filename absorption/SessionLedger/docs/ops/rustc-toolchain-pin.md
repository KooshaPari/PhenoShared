# Exact rustc toolchain pin (C06 L60)

Status: **done** for exact channel pin + hermetic SelfCheck. SessionLedger pins
an exact rustc release in [`rust-toolchain.toml`](../../rust-toolchain.toml)
(not floating `stable`) and records the matching `rustc -vV` commit-hash in
[`rustc-toolchain-pin.json`](rustc-toolchain-pin.json).

MSRV stays in workspace `Cargo.toml` (`rust-version = "1.85"`). The pin is the
**build** compiler; MSRV is the oldest supported compiler.

## Why exact (not `stable`)

Floating `stable` drifts whenever rustup updates. Exact `channel = "1.96.0"`
keeps local + CI compilers bit-identical until maintainers bump deliberately.

## Identity / SHA verify

| Field                       | Role                                              |
| --------------------------- | ------------------------------------------------- |
| `channel` / `rustc_release` | Exact rustup channel (semver)                     |
| `rustc_commit_hash`         | Content-addressed rustc identity from `rustc -vV` |
| rustup download digests     | rustup verifies channel artifacts when installing |

This pin does **not** claim SLSA L3 hermetic OS packages; see
[`hermetic-builds.md`](hermetic-builds.md).

## CI policy

Primary GitHub Actions jobs use `dtolnay/rust-toolchain` **without** a
`toolchain:` input so the action installs from `rust-toolchain.toml`. Jobs that
need nightly (fuzz / miri) may set `toolchain: nightly` intentionally.

Evidence workflows (non-exhaustive): `.github/workflows/ci.yml`,
`.github/workflows/hermetic.yml`, `.github/workflows/release.yml`.

## Bump procedure

1. Edit `rust-toolchain.toml` `channel` to the new exact version.
2. `rustup show` / `rustc -vV` and refresh `docs/ops/rustc-toolchain-pin.json`
   (`channel`, `rustc_release`, `rustc_commit_hash`, `rustc_commit_date`).
3. Run SelfCheck (below).
4. Land via PR; do not float back to `stable`.

## Machine verification (SelfCheck)

Hermetic pin + CI wiring smoke (no cargo build required for the script itself):

```powershell
pwsh ./scripts/rustc-toolchain-check.ps1 -SelfCheck
```

`-SelfCheck` asserts the pin file exists, the channel is an exact semver (not
`stable`/`beta`/`nightly`), the JSON identity matches the TOML channel, and
primary CI workflows install via `dtolnay/rust-toolchain` without overriding the
pin with `toolchain: stable`.

| Gate                                | Status   |
| ----------------------------------- | -------- |
| Exact rustc toolchain pin SelfCheck | **done** |

Soft CI (non-blocking): `.github/workflows/hermetic.yml` job
`rustc-toolchain-pin` runs the same `-SelfCheck` with `continue-on-error: true`.
