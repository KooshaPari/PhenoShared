# Session 2026-11-05 - browser profile generations and lease authority

## Goal

Give concurrent agents a real isolation boundary and a single-writer rule for browser
profiles. Before this change, agent browser work on this device bound each agent to its own
*browser window* inside one shared profile, so two agents driving the same origin shared
cookies, storage and authenticated session state. A window is a view, not an isolation
boundary.

Operator decision recorded at session start: **PhenoShared owns the browser implementation**
(resolving a blocker that had stalled an audit heartbeat for three weeks; see
`~/.loop/projects/wbs2-browser-review`, 833 ledger records with the identical
"exact existing implementation owner/name pending" blocker).

## What landed

New crate `crates/substrate-browser`:

| Module | Provides |
|---|---|
| `scope.rs` | [`Scope`] identifying `principal / profile / session [:tab]`, with a validated lowercase charset so a scope can safely be a path segment |
| `profile.rs` | [`ProfileStore`]: per-principal profiles made of numbered **generations**, each backed by its own browser data directory. Compare-and-swap `promote`, sealed-only `fork` (copy, never merge), guarded `remove` |
| `lease.rs` | [`LeaseManager`]: one writer per profile, TTL expiry, monotonic per-profile **fencing token**, `grant` / `renew` / `revoke` / `validate` / `sweep_expired` |
| `fsutil.rs` | Atomic temp-then-rename writes, 0700/0600 permissions, tree copy that never follows symlinks |

## Deliberate constraints

- **Exclusivity is per `principal/profile`, not per session or tab.** A browser profile is one
  storage jar; two holders would share cookies regardless of which window they drive. Tab-level
  multiplexing requires container-level storage isolation and is a later opt-in, not a default.
- **Forking requires a sealed source.** A sealed generation has no live reader. `fork` copies the
  directory tree and never merges two browser databases, because a browser profile has no merge
  semantics that preserve authenticated state.
- **Mutations are gated.** `ProfileStore::with_gate` refuses to rotate, seal, fork, promote or
  remove while a lease is held. `ProfileStore::new` is unguarded and is for setup and tests only.
- **Revocation advances the fence**, so a revoked holder cannot resume by re-reading a stale
  record.

## Scope boundary (what this is not)

This crate does not launch or drive a browser, and it does not implement a provider. It is the
state layer a broker sits on, kept browser-agnostic so the same authority covers Firefox, Chrome
over CDP, and remote workers.

Not done here, and still open on the project docket: a Chrome/CDP headless provider, profile
conformance tests against a real browser, a viewer routed to the exact lease, and cloud
placement.

## Verification

```
cargo test -p substrate-browser     # 24 passed (5 scope, 9 lease, 10 profile)
cargo clippy -p substrate-browser --all-targets -- -D warnings   # clean
cargo fmt -p substrate-browser -- --check                        # clean
```

Deterministic expiry is tested with an injected `Clock`, so none of the lease tests sleep.
