# Implementation Strategy — per-finding decision and change

Decision rule applied: **upgrade / remove the vulnerable parent whenever a fix
is reachable; only accept the risk when no upgrade exists, and then record a
single-crate, justified entry.** No blanket license or advisory waivers.

---

## Fixes applied (dependency changes)

### F1 — `pin-utils` (RUSTSEC-2026-0441, unmaintained) — **REMOVED**

`pin-utils` is an **optional** dependency of `loom 0.7.2`, enabled only by
loom's `futures` feature. `crates/sharecli-sync` is the only crate in the
workspace that enabled it, and it only uses `loom::sync::RwLock`,
`loom::model` and `loom::thread` — none of which need the `futures` feature.

Change — `crates/sharecli-sync/Cargo.toml`:

```toml
[target.'cfg(loom)'.dependencies]
loom = { version = "0.7" }        # was: features = ["futures"]

[dev-dependencies]
loom = { version = "0.7" }        # was: features = ["futures"]
```

Effect: `pin-utils` disappears from `Cargo.lock` entirely. **No ignore entry.**

### F2 — `crypto-bigint` (RUSTSEC-2026-0387, timing sidechannel) and

`rsa` (RUSTSEC-2023-0071, Marvin Attack) — **BOTH REMOVED**

These two were the only *vulnerability*-level findings, and the only ones
where a fix existed somewhere. The blocker was `jsonwebtoken 11`:

```toml
# jsonwebtoken 11.0.0 / 11.1.0
[dependencies.p256] version = "0.13.2"   # -> elliptic-curve 0.13 -> crypto-bigint 0.5
[dependencies.p384] version = "0.13.0"
[dependencies.rsa]  version = "0.9.6"    # behind the `rust_crypto` feature
```

`jsonwebtoken 11.1.0` is the newest published release and still pins the
`0.13.x` curve crates, so `crypto-bigint >= 0.7.6` is unreachable through it,
and `rsa` has no patch at all (`patched = []` in the advisory).

`jsonwebtoken` has two interchangeable crypto backends:

| backend | feature | pulls |
|---|---|---|
| RustCrypto | `rust_crypto` | `rsa`, `p256`, `p384`, `ecdsa`, `elliptic-curve`, `primeorder`, `crypto-bigint`, `ed25519-dalek` |
| AWS-LC | `aws_lc_rs` | `aws-lc-rs` |

Both backends implement the **same** algorithm set that this workspace uses
(`HS256/384/512`, `ES256`, `ES384`, `RS256/384/512`, `PS256/384/512`, `EdDSA`),
and both provide `DecodingKey::from_rsa_components` / `from_ec_components`
and a fully-implemented `KeyUtils` — verified in the `jsonwebtoken 11.0.0`
source (`src/crypto/aws_lc/{mod,rsa,ecdsa}.rs`, `src/decoding.rs`).

Change — `crates/sharecli/Cargo.toml`:

```toml
jsonwebtoken = { version = "11", features = ["use_pem", "aws_lc_rs"] }
# was: features = ["use_pem", "rust_crypto"]
```

`aws-lc-rs` was **already** a transitive dependency of `sharecli`
(`reqwest` → `hyper-rustls` → `rustls` → `aws-lc-rs`), so this swap adds **no
new build dependency** and no new toolchain requirement.

Effect: `rsa`, `p256`, `p384`, `ecdsa`, `elliptic-curve`, `primeorder` and
`crypto-bigint` all disappear from `Cargo.lock`. **No ignore entries** for
either advisory.

### F3 — `iac` workspace: `rustls-webpki` + `webpki-roots` — **UPGRADED**

Both advisories had published fixes inside the same version family, so they
were upgraded rather than ignored:

```bash
cd iac
cargo update -p webpki-roots   --precise 1.0.10    # 1.0.8  -> 1.0.10
cargo update -p rustls-webpki --precise 0.103.16   # 0.103.15 -> 0.103.16
```

Only `iac/Cargo.lock` changed; `iac/deny.toml` was not touched.

---

## Risk acceptances recorded (root `deny.toml`)

Six advisories remain, all **unmaintained** (not vulnerability/unsound). Each
has a dedicated comment block in `deny.toml` naming the crate, the exact
dependency path, why no upgrade removes it, and the residual risk. The
advisory IDs were added to `[advisories].ignore`:

| Advisory ID | Crate | Path summary | Why unavoidable |
|---|---|---|---|
| `RUSTSEC-2026-0374` | `basic-toml 0.1.10` | `askama_derive 0.14` → `askama 0.14` → `uniffi_bindgen 0.31.2` → `uniffi_build` → `eyetracker-ffi` (build-dep); `focus-entitlements` (dev-dep) | last release ever; `askama_derive 0.16.1` still uses `basic-toml ^0.1.1` |
| `RUSTSEC-2026-0249` | `smartstring 1.0.1` | `phenotype-casbin-wrapper` → `casbin 2.20.0` → `rhai 1.26.1` | advisory: all versions affected; `rhai 1.27.0` still has it as a **mandatory** dep |
| `RUSTSEC-2024-0449` | `unsafe-libyaml 0.2.11` | `serde_yaml 0.9.34+deprecated` ← 13 workspace crates + `figment` | `serde_yaml` deprecated; recommended fork `serde_yaml_ng 0.10.0` **also** depends on `unsafe-libyaml ^0.2.11` |
| `RUSTSEC-2026-0371` | `zbus_names 4.3.4` | `zbus 5.19.0` ← `ashpd 0.11.1`, `ksni 0.3.6`, `secret-service 5.2.0` | merged into `zbus 6.0.0`; `ksni` has **no** zbus-6 release |
| `RUSTSEC-2026-0370` | `zvariant 5.15.0` | `zbus 5.19.0` / `zbus_macros 5.19.0` | same zbus-6 wall |
| `RUSTSEC-2026-0372` | `zvariant_derive 5.15.0` | `zbus_macros 5.19.0` | same zbus-6 wall |

**No entry was added for `crypto-bigint` or `rsa`** — those were fixed.

---

## License exception (root `deny.toml`)

`GPL-3.0` was **not** added to `[licenses].allow`. It is granted only to the
two WinFsp crates via the cargo-deny 0.20 per-crate exception list:

```toml
[licenses]
# ...
exceptions = [
    { crate = "winfsp", allow = ["GPL-3.0"] },
    { crate = "winfsp-sys", allow = ["GPL-3.0"] },
]
```

Justification: both crates are the WinFsp FUSE bindings pulled in by
`crates/sharecli-fuse` under `[target.'cfg(windows)'.dependencies]` and
`[target.'cfg(windows)'.build-dependencies]` only. Any *other* crate in the
workspace using GPL-3.0 is still rejected by the `allow` list.

Schema note: cargo-deny 0.20 requires `exceptions` to be an **array of
tables** inside `[licenses]` (a `[licenses.exceptions]` sub-table or a
`crate -> license` map is a parse error), and each table needs a `crate` key
plus an `allow` **array**.

---

## Files changed

| File | Change |
|---|---|
| `deny.toml` | +6 documented advisory ignores, +2 per-crate GPL-3.0 license exceptions |
| `crates/sharecli/Cargo.toml` | `jsonwebtoken` backend `rust_crypto` → `aws_lc_rs` |
| `crates/sharecli-sync/Cargo.toml` | dropped loom's unused `futures` feature |
| `Cargo.lock` | `rsa`/`p256`/`p384`/`ecdsa`/`elliptic-curve`/`primeorder`/`crypto-bigint`/`pin-utils` removed |
| `iac/Cargo.lock` | `rustls-webpki` 0.103.15 → 0.103.16, `webpki-roots` 1.0.8 → 1.0.10 |
| `docs/sessions/2026-11-07-cargo-deny-findings/` | this session record |
