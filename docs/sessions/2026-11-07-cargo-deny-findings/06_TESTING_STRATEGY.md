# Testing Strategy / Validation Record

All commands were run locally in
`/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared` on
`fix/cargo-deny-findings` with `cargo-deny 0.20.2` (the version
`cargo install cargo-deny --locked` resolves to in CI).

## 1. The gate itself

### Root workspace — before

```console
$ cargo deny check --hide-inclusion-graph
...
advisories FAILED, bans ok, licenses FAILED, sources ok
EXIT=5          # 11 errors: 2 license rejections + 9 advisories
```

### Root workspace — after

```console
$ cargo deny check --hide-inclusion-graph
...
advisories ok, bans ok, licenses ok, sources ok
EXIT=0          # 0 errors
```

Error count by class, before → after:

| class | before | after |
|---|---|---|
| `error[rejected]` (license) | 2 | 0 |
| `error[vulnerability]` | 2 | 0 |
| `error[unmaintained]` | 7 | 0 |
| **total errors** | **11** | **0** |

Remaining output is warnings only: 141 `warning[duplicate]`,
2 `warning[license-not-encountered]`, 2 `warning[parse-error]` — all
pre-existing except the two WinFsp `parse-error` warnings, which come from
the upstream crates' own `Cargo.toml`.

### The exact four CI steps (`.github/workflows/deny.yml`)

```console
$ for c in licenses advisories bans sources; do
    cargo deny check $c --hide-inclusion-graph >/dev/null 2>&1 && echo "$c PASS" || echo "$c FAIL"
  done
licenses     PASS
advisories   PASS
bans         PASS
sources      PASS
```

### `iac` workspace — before → after

```console
$ cd iac && cargo deny check --hide-inclusion-graph
# before: EXIT=1, 2 errors (RUSTSEC-2026-0382 rustls-webpki, RUSTSEC-2026-0381 webpki-roots)
# after:
advisories ok, bans ok, licenses ok, sources ok
EXIT=0
```

## 2. Dependency-graph assertions

```console
$ grep -c 'name = "<crate>"' Cargo.lock
rsa                0     # was 1
p256               0     # was 1
p384               0     # was 1
ecdsa              0     # was 1
elliptic-curve     0     # was 1
primeorder         0     # was 1
crypto-bigint      0     # was 1
pin-utils          0     # was 1
```

`iac/Cargo.lock`: `rustls-webpki` 0.103.15 → 0.103.16,
`webpki-roots` 1.0.8 → 1.0.10.

## 3. Build + test of the touched crates

| Command | Result |
|---|---|
| `cargo check -p sharecli --all-targets` | **exit 0** (only pre-existing warnings) |
| `cargo test -p sharecli --test fr012_serve_jwt_auth` | **3 passed, 0 failed** |
| `cargo test -p sharecli` (full suite) | **190 passed, 0 failed, 5 ignored**, exit 0 |
| `cargo test -p sharecli-sync` | exit 0 (no non-loom tests) |
| `RUSTFLAGS="--cfg loom" cargo test -p sharecli-sync --test loom_pool_index` | **3 passed, 0 failed** |

The `fr012_serve_jwt_auth` suite is the direct regression test for the JWT
backend swap: it exercises valid-JWT acceptance, expiry rejection, and
audience/issuer rejection through `crates/sharecli/src/serve_auth.rs`, which
is the code that uses `jsonwebtoken`'s verifier and `DecodingKey::from_rsa_components`
/ `from_ec_components`.

The `sharecli-sync` loom suite is the direct regression test for the loom
feature removal: it is the only consumer of loom in `sharecli-sync` and it
compiles and runs under `--cfg loom` without the `futures` feature.

## 4. Not verified

* **Windows builds.** `winfsp`/`winfsp-sys` are `cfg(windows)`-gated and were
  not compiled here (macOS host). The change to them is config-only — no
  source or dependency edit — so the Windows build path is unchanged.
* **`cargo build --workspace`.** Only the crates touched by this change
  (`sharecli`, `sharecli-sync`, and their dependents) were compiled and
  tested; a full 279-member workspace build was not run. The `Cargo.lock`
  delta only *removes* packages, so no new crate needs to compile.
* **`cargo audit` / `osv-scanner` / `gitleaks` CI jobs** were not run.
