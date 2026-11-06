# Session 2026-11-05 - browser broker: profiles, leases, CDP, viewer, deploy

Continuation of `docs/sessions/2026-11-05-browser-profile-lease/00_SESSION_OVERVIEW.md`.
That session landed the state layer. This one makes it drive a real browser.

## What landed

### `crates/substrate-browser-cdp` - a real DevTools provider

| File | Responsibility |
|---|---|
| `launch.rs` | Find Chrome (`CHROME_BIN`, then platform paths), spawn it with `--remote-debugging-port=0` and a caller-owned `--user-data-dir`, read the endpoint off stderr, kill on drop |
| `transport.rs` | One WebSocket, serialized request/response, events discarded, per-command timeout |
| `snapshot.rs` | Normalize `Accessibility.getFullAXTree` into the protocol's node/element shape, giving every actionable node a stable `element_ref` |
| `provider.rs` | `open`, `snapshot`, `click`, `type_into`, `wait_for_text`, `screenshot`, `eval`, `title`, `url`, `close` |

The accessibility tree is the read surface because it is what the browser already
computed for assistive technology, it survives DOM churn, and each actionable node
carries a `backendDOMNodeId` that resolves back to a live element.

### `crates/substrate-browser-broker` - the enforcing layer

`Broker::acquire` is the whole point: ensure the profile, resolve the active
generation, **grant the lease**, launch the browser **on that generation's data
directory**, publish the session under the lease id. A failed launch revokes the
lease so a broken browser cannot hold a profile.

`release` reverses it: close the browser, revoke the lease, seal the generation
(sealing requires no live reader, which is why the order matters).

### Viewer (B4)

`GET /v1/view/{lease_id}/png` renders **that** lease's page. A lease that is not
live returns 404; there is no heuristic that picks "a browser". Bearer-token auth
with a constant-time compare, and `brokerd` refuses to bind a non-loopback address
without a token.

### Deployment (B5)

`deploy/browser-broker/` carries a `Containerfile`, a hardened systemd unit and a
README covering the loopback-plus-tunnel shape.

**Explicitly unverified:** these manifests were written from the binary's real CLI
surface but have not run on a cloud host, because that needs `jcode login`. The
README says so at the top rather than implying a deployment.

## Deliberate limits, stated rather than hidden

- **One in-flight CDP command per connection.** Concurrency comes from separate
  browsers, not from multiplexing one socket. This removes a class of routing bugs
  and costs nothing the broker needs.
- **Exclusivity stays per profile**, not per tab. A profile is one cookie jar.
- **No TLS in `brokerd`.** Loopback and tunnel, or nothing.
- **Leases are not reaped on crash.** A killed broker leaves records until TTL;
  `sweep_expired` runs on the next grant so the window is bounded.
- **One bearer token sees every session.** Per-principal authorisation is a later
  change, named in the deploy README.

## Verification

All of the following ran on this host against **real headless Chrome 152**:

```
cargo test -p substrate-browser           # 24 passed
cargo test -p substrate-browser-cdp       # 3 unit + 2 live = 5 passed
cargo test -p substrate-browser-broker    # 4 passed
cargo clippy -p ... --all-targets -- -D warnings   # clean
cargo fmt -p ... -- --check                        # clean
```

The live tests prove, not simulate:

1. launch, navigate, read the accessibility tree, click by reference, type and
   submit, evaluate JavaScript, and capture a real PNG;
2. two data directories do **not** share `localStorage`;
3. two agents acquire two profiles concurrently and stay isolated;
4. a second acquire on a leased profile is refused and leaks no session;
5. release seals the generation and lets the next agent take over;
6. the viewer returns a PNG for the exact lease, 404 for an unknown one, and 401
   without the token.

## Follow-up: lease-fenced handles (2026-11-06)

A later pass changed how callers reach the browser. `BrowserHandle` no longer
exposes a raw `&mut CdpProvider`. The provider guard is private to the module,
so a caller can only ask for a named action: `open`, `snapshot`, `click`,
`type_into`, `wait_for_text`, `screenshot`, `eval`, `title`, `url`, `pid`.
Authority therefore cannot be held past the check that granted it.

### Lease re-validation

`LeaseGuard` (`src/lease_guard.rs`) re-proves the lease against the on-disk
`LeaseManager`: the record still exists, it has not expired on the manager's
clock, and the presented fencing token is still current. Any failure is an
error; there is no degraded mode.

Each action runs that check twice: before taking the browser, and again after
the wait for the browser, because waiting may have outlived the lease.

### Bounded waits

The wait for the browser is capped at 30 seconds. A DevTools call that stays
stuck returns `BrokerError::Busy` instead of wedging `release`, `reap`, or
`acquire`.

`shutdown()` is bounded on the same budget. `CdpProvider` kills its child on
drop, so a close that times out cannot leave a live browser behind.

### Module layout

`BrowserHandle` lives in its own module, `src/handle.rs`, and `lib.rs` is 460
lines, under the 500-line limit.

### Residual risk, still open

- An action already in flight when the lease expires can complete. Enforcement
  is per-action, not per-CDP-message.
- Cross-process authority rests on the on-disk lease and its file lock. That
  path has not been soak-tested.
