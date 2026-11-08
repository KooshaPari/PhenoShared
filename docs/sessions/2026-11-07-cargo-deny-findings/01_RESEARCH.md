# Research — full cargo-deny findings and dependency paths

Tooling: `cargo-deny 0.20.2` (the version `cargo install cargo-deny --locked`
resolves to in CI), local `~/.cargo/advisory-db` RUSTSEC snapshot.

Command used for the root workspace (same graph CI audits):

```bash
cargo deny check --hide-inclusion-graph     # full run
cargo deny check licenses|advisories|bans|sources   # the 4 CI steps
```

`iac` is a **separate workspace** with its own `Cargo.lock` and its own
`iac/deny.toml`; it is audited by `.github/workflows/cargo-deny.yml`
(`manifest-path: iac/Cargo.toml`).

---

## A. Root workspace — before state (exit 5, 11 errors)

### A.1 License rejections (2)

| # | Crate | Version | License | cargo-deny verdict |
|---|---|---|---|---|
| L1 | `winfsp` | `0.13.1+winfsp-2.1` | `GPL-3.0` | `error[rejected]: failed to satisfy license requirements` |
| L2 | `winfsp-sys` | `0.12.1+winfsp-2.1` | `GPL-3.0` | `error[rejected]: failed to satisfy license requirements` |

Both crates also emit `warning[parse-error]` because upstream declares the
deprecated SPDX id `GPL-3.0` (cargo-deny wants `GPL-3.0-only`). The warning
comes from the upstream `Cargo.toml`, not from our config, and does not fail
the gate.

**Dependency path** (`cargo tree --target all -i winfsp`):

```
winfsp v0.13.1+winfsp-2.1
[build-dependencies]
└── sharecli-fuse v0.8.0 (crates/sharecli-fuse)
    ├── sharecli v0.8.0
    ├── sharecli-core v0.8.0
    └── sharecli-thermal-tui v0.8.0
```

`crates/sharecli-fuse/Cargo.toml` scopes it to Windows only:

```toml
[target.'cfg(windows)'.dependencies]
winfsp = { version = "0.13", features = ["full", "windows-61"] }

[target.'cfg(windows)'.build-dependencies]
winfsp = { version = "0.13", features = ["build", "delayload"] }
```

So: **platform-specific (Windows-only), target-gated, plus a Windows-only
build-dependency.** It is never compiled on the macOS/Linux CI runners.

### A.2 Advisory failures (9)

| # | Crate | Version | Advisory | Level | cargo-deny verdict |
|---|---|---|---|---|---|
| V1 | `basic-toml` | `0.1.10` | RUSTSEC-2026-0374 | unmaintained | `error[unmaintained]` — "No safe upgrade is available!" |
| V2 | `crypto-bigint` | `0.5.5` | RUSTSEC-2026-0387 | vulnerability | `error[vulnerability]` — "Upgrade to >=0.7.6" |
| V3 | `pin-utils` | `0.1.1` | RUSTSEC-2026-0441 | unmaintained | `error[unmaintained]` — "No safe upgrade is available!" |
| V4 | `rsa` | `0.9.10` | RUSTSEC-2023-0071 | vulnerability | `error[vulnerability]` — "No safe upgrade is available!" |
| V5 | `smartstring` | `1.0.1` | RUSTSEC-2026-0249 | unmaintained | `error[unmaintained]` — "No safe upgrade is available!" |
| V6 | `unsafe-libyaml` | `0.2.11` | RUSTSEC-2024-0449 | unmaintained | `error[unmaintained]` — "No safe upgrade is available!" |
| V7 | `zbus_names` | `4.3.4` | RUSTSEC-2026-0371 | unmaintained | `error[unmaintained]` — "No safe upgrade is available!" |
| V8 | `zvariant` | `5.15.0` | RUSTSEC-2026-0370 | unmaintained | `error[unmaintained]` — "No safe upgrade is available!" |
| V9 | `zvariant_derive` | `5.15.0` | RUSTSEC-2026-0372 | unmaintained | `error[unmaintained]` — "No safe upgrade is available!" |

V2 is the *timing sidechannel* advisory (constant-time branches in
`crypto-bigint` 0.5.5: subtraction, zero counting, division, Montgomery
multiplication, `UintRef` equality, `BoxedMontyForm::invert`).
V4 is the *Marvin Attack* advisory (RUSTSEC-2023-0071).

**Dependency paths** (`cargo tree -i <crate>`, `--target all` where the crate
is target-specific):

```
basic-toml v0.1.10
└── askama_derive v0.14.0 (proc-macro)
    └── askama v0.14.0
        ├── uniffi_bindgen v0.31.2
        │   └── uniffi_build v0.31.2
        │       └── uniffi v0.31.2
        │           [build-dependencies]
        │           └── eyetracker-ffi v0.1.0-alpha (crates/eyetracker-ffi)
        └── uniffi_bindgen v0.31.2
            └── uniffi v0.31.2
                ├── eyetracker-ffi v0.1.0-alpha
                └── focus-entitlements v0.3.10
                [dev-dependencies]
```

```
crypto-bigint v0.5.5
└── elliptic-curve v0.13.8
    ├── ecdsa v0.16.9
    │   ├── p256 v0.13.2
    │   │   └── jsonwebtoken v11.0.0
    │   │       └── sharecli v0.8.0 (crates/sharecli)
    │   └── p384 v0.13.1
    │       └── jsonwebtoken v11.0.0
    ├── p256 v0.13.2
    ├── p384 v0.13.1
    └── primeorder v0.13.6
```

```
pin-utils v0.1.1
└── loom v0.7.2
    [dev-dependencies]
    ├── pheno-otel v0.1.0 (crates/argis-extensions/pheno-otel)
    └── sharecli-sync v0.8.0 (crates/sharecli-sync)
        └── sharecli v0.8.0
```

```
rsa v0.9.10
└── jsonwebtoken v11.0.0
    └── sharecli v0.8.0 (crates/sharecli)
        ├── sharecli-ffi v0.8.0
        └── sharecli-ipc v0.8.0
```

```
smartstring v1.0.1
└── rhai v1.26.1
    └── casbin v2.20.0
        └── phenotype-casbin-wrapper v0.2.0
```

```
unsafe-libyaml v0.2.11
└── serde_yaml v0.9.34+deprecated
    ├── acceptance-contract v0.3.10
    ├── dag-scheduler v0.3.10
    ├── fabric-cli v0.1.0
    ├── figment v0.10.19
    │   ├── pheno-config v0.1.0
    │   └── phenotype-config v0.3.10
    ├── phenocompose-cli v0.1.0
    ├── phenotype-config v0.3.10
    ├── phenotype-config-core v0.2.0
    ├── phenotype-dag-core v0.1.0
    ├── phenotype-journey-core v0.3.10
    ├── phenotype-shared-config v0.3.10
    ├── qgate v0.3.10
    └── sharecli v0.8.0
```

```
zbus_names v4.3.4
├── zbus v5.19.0
│   ├── ashpd v0.11.1 → eidolon-desktop v0.3.10
│   ├── ksni v0.3.6 → sharecli-tray-linux v0.8.0
│   └── secret-service v5.2.0 → focus-crypto v0.3.10
└── zbus_macros v5.19.0 (proc-macro)

zvariant v5.15.0        ← zbus v5.19.0, zbus_macros v5.19.0, zbus_names v4.3.4
zvariant_derive v5.15.0 ← zbus_macros v5.19.0, zvariant v5.15.0
```

---

## B. `iac` workspace — before state (exit 1, 2 errors)

| Crate | Version | Advisory | Verdict |
|---|---|---|---|
| `rustls-webpki` | `0.103.15` | RUSTSEC-2026-0382 | `error[vulnerability]` — "Upgrade to >=0.103.16, <0.104.0-alpha.1" |
| `webpki-roots` | `1.0.8` | RUSTSEC-2026-0381 | `error[vulnerability]` — "Upgrade to >=1.0.10" |

Both are the "emSign intermediate public keys are well known" trust-store
issue, reached via `reqwest` → `rustls` → `rustls-webpki` / `webpki-roots`.

---

## C. Upstream-version research (crates.io index, read 2026-11-07)

Used to decide fix-vs-accept per finding.

| Crate | Newest published | Drops the problem? |
|---|---|---|
| `crypto-bigint` | `0.7.10` (fix is `>=0.7.6`; `0.7.6`–`0.7.8` are **yanked**) | **yes**, but only via `elliptic-curve >= 0.14` → `p256/p384 >= 0.14`; `crypto-bigint 0.5.5` is the last `0.5.x` ever published |
| `elliptic-curve` | `0.14.3` | yes — `0.14.x` uses `crypto-bigint 0.7.x` |
| `p256` / `p384` | `0.14.0` | yes — `0.14` uses `elliptic-curve 0.14` |
| `jsonwebtoken` | `11.1.0` | **no** — still `p256 = "0.13.2"`, `p384 = "0.13.0"` (0.x minor bumps are semver-breaking), so `jsonwebtoken 11.x` can never reach `elliptic-curve 0.14` |
| `rsa` | `0.9.10` (stable), `0.10.0-rc.18` (pre-release) | **no** — advisory states `patched = []` intentionally; both are still affected |
| `askama_derive` | `0.16.1` | **no** — still `basic-toml = "^0.1.1"` |
| `uniffi_bindgen` | `0.32.2` | **no** — only bumps askama to `^0.16.0`, which still uses `basic-toml` |
| `rhai` | `1.27.0` | **no** — `smartstring = "1.0.0"` is still a **mandatory** (non-optional) dep |
| `casbin` | `2.20.0` | **no** — unchanged |
| `serde_yaml` | `0.9.34+deprecated` | **no** — deprecated, no successor |
| `serde_yaml_ng` (recommended fork) | `0.10.0` | **no** — still `unsafe-libyaml = "^0.2.11"` |
| `zbus` | `6.2.1` | yes in principle, but see `ksni` below |
| `ashpd` | `0.14.0` (accepts `zbus ^6.0.0`) | only with a zbus-6 bump |
| `secret-service` | `6.0.0-rc.1` (accepts `zbus ^6`) | pre-release only |
| `ksni` | `0.3.7` | **no** — every `ksni` release requires `zbus ^5`; there is **no zbus 6 release of `ksni`** |
| `loom` | `0.7.2` | `pin-utils` is **optional**, enabled only by loom's `futures` feature |
| `basic-toml` | `0.1.10` | **no** — last release, repo archived 2025-03-04 |
| `smartstring` | `2.0.0` | **no** — advisory says *all* versions affected; rhai pins `^1.0.0` anyway |
| `pin-utils` | `0.1.1` | **no** — last release, repo archived 2026-10-01 |
