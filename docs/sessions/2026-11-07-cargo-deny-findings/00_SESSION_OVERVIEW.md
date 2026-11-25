# Session Overview — cargo-deny CI gate

**Session ID:** 2026-11-07-cargo-deny-findings
**Date:** 2026-11-07
**Branch:** `fix/cargo-deny-findings` (from `main` @ `535116dd`)
**Scope:** make the `cargo-deny` CI jobs green without blanket-waiving any
license or advisory.

## Problem

Two CI jobs are named `cargo-deny`:

| Workflow | Job | Target | Config |
|---|---|---|---|
| `.github/workflows/deny.yml` | `deny` (display name `cargo-deny`) | root workspace | `./deny.toml` |
| `.github/workflows/cargo-deny.yml` | `cargo-deny` | `iac/Cargo.toml` | `./iac/deny.toml` |

Both were red:

* Root workspace: **11 errors** — 2 license rejections (`winfsp`,
  `winfsp-sys` under GPL-3.0) and 9 advisory failures.
* `iac` workspace: **2 errors** — `rustls-webpki` RUSTSEC-2026-0382 and
  `webpki-roots` RUSTSEC-2026-0381 (emSign intermediate distrust).

## Success criteria

1. Every finding is identified with crate, advisory ID, version and license.
2. Every finding's real dependency path is established (`cargo tree -i`).
3. Findings are fixed by upgrade wherever a fix is reachable, and only
   *accepted* (with a per-crate, justified `deny.toml` entry) where no fix
   exists.
4. `cargo deny check licenses|advisories|bans|sources` exits 0 in both
   workspaces, using the same commands CI runs.
5. The change is committed on `fix/cargo-deny-findings` and pushed, unmerged.

## Result

| Metric | Before | After |
|---|---|---|
| Root workspace `cargo deny check` | exit 5, **11 errors** | exit 0, **0 errors** |
| `iac` workspace `cargo deny check` | exit 1, **2 errors** | exit 0, **0 errors** |
| Vulnerable crates in root `Cargo.lock` | `rsa`, `p256`, `p384`, `ecdsa`, `elliptic-curve`, `primeorder`, `crypto-bigint`, `pin-utils` (8) | 0 |

## Constraints honoured

* No blanket license allowance — `GPL-3.0` was **not** added to
  `[licenses].allow`; it is granted only to `winfsp` and `winfsp-sys` via
  `[licenses].exceptions`.
* No advisory waived that has a reachable fix. `crypto-bigint` and `rsa` were
  removed from the tree entirely rather than ignored.
* The six remaining advisory ignores each name a single RUSTSEC ID, the
  exact dependency path, why no upgrade removes it, and the residual risk.
* No files deleted. No merge to `main`. No `gh` usage.
