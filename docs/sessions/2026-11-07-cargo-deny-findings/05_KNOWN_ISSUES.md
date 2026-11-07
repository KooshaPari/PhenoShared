# Known Issues / Residual Risk

## Accepted advisories (root `deny.toml`)

Six `unmaintained` advisories are accepted. All are recorded per-crate in
`deny.toml` with the dependency path and the reasoning. Summary of residual
exposure:

| Advisory | Crate | Residual exposure |
|---|---|---|
| RUSTSEC-2026-0374 | `basic-toml 0.1.10` | build-time / proc-macro only; parses in-tree `Cargo.toml` templates, never untrusted input |
| RUSTSEC-2026-0249 | `smartstring 1.0.1` | string arena inside the `rhai` Casbin expression engine; no CVE |
| RUSTSEC-2024-0449 | `unsafe-libyaml 0.2.11` | c2rust translation of libyaml C code, used to parse trusted config files only |
| RUSTSEC-2026-0371 | `zbus_names 4.3.4` | D-Bus well-known-name types; no CVE |
| RUSTSEC-2026-0370 | `zvariant 5.15.0` | D-Bus wire-format codec; no CVE |
| RUSTSEC-2026-0372 | `zvariant_derive 5.15.0` | proc-macro derive only; no CVE |

None of these is a `vulnerability` or `unsound` advisory — all are
"unmaintained", i.e. the upstream repository stopped being maintained.
Revisit when any of the blockers below clears.

### Blockers to clearing each acceptance

| Advisory | Blocker | What would clear it |
|---|---|---|
| RUSTSEC-2026-0374 | `askama_derive` always depends on `basic-toml` | `askama_derive` dropping `basic-toml`, or `uniffi` dropping `askama` |
| RUSTSEC-2026-0249 | `rhai` has `smartstring` as a mandatory dep | `rhai` replacing `smartstring` with `compact_str`/`smol_str`, or `casbin` dropping `rhai` |
| RUSTSEC-2024-0449 | `serde_yaml` deprecated; `serde_yaml_ng` also uses `unsafe-libyaml` | migrate 13 crates + `figment` to a safe-Rust YAML parser (`saphyr` / `noyalib`) |
| RUSTSEC-2026-0371/0370/0372 | `ksni` has no `zbus` 6 release | `ksni` publishing a zbus-6 release, then a zbus 5 → 6 migration of `eidolon-desktop`, `sharecli-tray-linux`, `focus-crypto` |

## Accepted license exception (root `deny.toml`)

`winfsp` and `winfsp-sys` (GPL-3.0) are permitted via `[licenses].exceptions`
only. They are `cfg(windows)`-gated in `crates/sharecli-fuse` and are not
compiled or redistributed in the macOS/Linux artifacts. If the Windows FUSE
mount is ever removed, these exceptions should be dropped.

## Non-blocking warnings left in place

`cargo deny check` still emits warnings (not errors, so the gate passes):

* `warning[parse-error]` ×2 — `winfsp` / `winfsp-sys` declare the deprecated
  SPDX id `GPL-3.0` instead of `GPL-3.0-only`. This originates in the
  upstream crates' own `Cargo.toml`; cargo-deny exposes no config knob for it.
* `warning[license-not-encountered]` ×2 — `CC-BY-4.0` and
  `Unicode-DFS-2016` are in `[licenses].allow` but no crate in the tree
  currently uses them. Pre-existing.
* `warning[duplicate]` ×141 — multiple versions of the same crate.
  `[bans].multiple-versions = "warn"` is intentional in this repo. Also
  pre-existing.

## Out of scope

* The `iac` workspace still warns about the yanked `chacha20 0.10.1`. It is
  reachable there (`rand 0.10.3` → `oci-lottery`, and `rand 0.10.3` requires
  `chacha20 ^0.10.0`), but cargo-deny 0.20's default for
  `[advisories].yanked` is `warn`, so the `iac` gate passes. `iac/deny.toml`
  does not set `yanked`, and the root `deny.toml` sets `yanked = "warn"`
  explicitly. Left alone to keep this change focused on the reported
  findings.
* `cargo-audit` / `osv-scanner` / `gitleaks` CI jobs were not audited.
