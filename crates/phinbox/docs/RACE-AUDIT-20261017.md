# Permission JSON race audit — 2026-10-17

Branch: `feat/phinbox-full-intent-20261017` (HEAD `4836ac9b`)
Scope: concurrent submitters across HTTP / IPC / CLI channels on the same
`request_id`. Audit-only; no code changes proposed for this commit.
Receipt for the "first answer stands" invariant.

## TL;DR

The "first answer stands" invariant is **not enforced under concurrency**.
Three independent submission paths (HTTP form handler, IPC JSON-RPC, CLI
`phinbox answer`) all follow the same `load → expire_if_due → check
is_terminal → finalize` pattern. There is **no file lock and no
compare-and-swap** between the check and the write. Two concurrent submitters
in different channels can both pass the `is_terminal` check while the
request is still `Pending`, and the second `finalize` overwrites the first
answer in `answered/{id}.json`. The atomic `fs::write` + `fs::rename` inside
`finalize` is a single-file atomic write, not a CAS over the read+check
sequence.

The existing test surface in
`crates/phinbox/src/inbox/daemon/{tests.rs,form/tests.rs}` and
`crates/phinbox/src/cli/answer.rs` covers **sequential** behavior only
(e.g. `http_reanswer_is_refused_and_the_first_answer_stands` posts A
then B in series). No test exercises two submitter threads racing on
the same `request_id`.

## What is already correct (and protects against what)

1. **`fs::write` + `fs::rename` is atomic on POSIX** — readers see either
   the pre-rename or post-rename file, never a torn write. Used in
   `mark.rs::{enqueue, finalize}` and `expire.rs::mark_expired_in_place`.
   This protects **individual** file writes from each other, not the
   read-then-write pattern across them.
2. **`expire_if_due` is lazy and idempotent** — two concurrent readers
   that both see the same expired pending request will both transition
   to `Expired` and both call `mark_expired_in_place`. The state is the
   same, so the second write is a no-op semantically (though the file
   mtime is bumped twice).
3. **`InboxChangeBus`** notifies `wait_for_response` subscribers on every
   `enqueue`/`finalize`. Waiters see the latest state on next load, so
   even with the race, the final answer a waiter sees is consistent
   (it's the second writer's).
4. **Lockfile `live_url` is a discovery hint, not a serialization
   point.** Two daemons cannot share a port, and the second
   `write_lockfile` would clobber the first. This is mitigated by
   `is_port_live` probing, but the write itself is non-atomic
   (`std::fs::write`, no rename — see `lockfile.rs:53`).

## Race 1 — HTTP form handler (`submit_answer` in `daemon/form/mod.rs`)

**File:** `crates/phinbox/src/inbox/daemon/form/mod.rs:76-218`

```
submit_answer(root, request_id, body):
  req = load(root, request_id)            // read inbox/ or answered/
  expire_if_due(root, &mut req)           // may write inbox/{id}.json (Pending → Expired)
  if req.is_terminal() return Err(AlreadyFinalized)
  ... process body ...
  finalize(root, &final_req)              // write answered/{id}.json (atomic rename)
```

The HTTP server uses one thread per connection
(`daemon/http/mod.rs:80: thread::spawn(move || { handle_connection(...) })`).
Two concurrent POSTs to `/inbox/{id}/answer` therefore run in parallel
threads.

**Race window:** between `load` (line 89) and `finalize` (line 216).
Both threads can read the same `Pending` request, both pass the
`is_terminal()` check (line 106), and both proceed to `finalize`. The
second `finalize` renames over `answered/{id}.json` with its own
`PendingRequest { state, response }` — the first answer is overwritten.

**Mitigations already in place for this channel:** none. The check
is "check-then-write" with no inter-thread serialization.

## Race 2 — IPC JSON-RPC (`finalize_via_state` in `ipc/server.rs`)

**File:** `crates/phinbox/src/inbox/ipc/server.rs:194-300`

```
finalize_via_state(state, rid, response):
  pending = load_pending(&state.root, rid)
  expire_if_due(&state.root, &mut pending)
  if !matches!(pending.state, RequestState::Pending) return Err(BadState)
  pending.state = new_state
  pending.response = Some(response)
  crate::inbox::finalize(&state.root, &pending)   // same atomic-rename write
```

Identical race window. The IPC server runs on a Unix domain socket and
dispatches per-connection tasks on tokio (or thread::spawn, depending on
the runtime). Two clients can race the same `request_id`.

**Special case for `ElicitResponse::Deferred`:** the defer path does
**not** call `finalize`; it writes the deferred response back to
`inbox/{id}.json` (line 270-273) so the request stays answerable.
This is also a non-CAS write — two concurrent defers can both write
their own `Deferred` response, and the last write wins. The semantic
loss here is small (defer is not a final answer), but the race is
real.

## Race 3 — CLI `phinbox answer` (`cmd_answer` in `cli/answer.rs`)

**File:** `crates/phinbox/src/cli/answer.rs:34-113`

```
cmd_answer(args, inbox_dir):
  req = load(inbox_dir, &args.request_id)
  expire_if_due(inbox_dir, &mut req)
  if req.is_terminal() return Err
  ... build response ...
  req.state = ...; req.response = Some(response)
  finalize(inbox_dir, &req)
```

Each `phinbox answer` invocation is a separate process, so two
concurrent CLI invocations from different shells race in the same way
as the HTTP case. The CLI does not consult the daemon; it writes
`answered/{id}.json` directly via `finalize`.

## Race 4 — Lockfile write (`write_lockfile` in `daemon/lockfile.rs`)

**File:** `crates/phinbox/src/inbox/daemon/lockfile.rs:38-55`

```
std::fs::write(path, json)   // line 53 — NOT write+rename
```

Two daemons starting at the same instant can both pass the
`is_port_live` check (because neither has bound the port yet) and
both call `write_lockfile`. The second `fs::write` clobbers the
first. This is a daemon-startup race; in practice, the second daemon
fails its `bind()` and exits, but its `daemon.lock` may be left
behind pointing at a port that is now closed.

## Race 5 — Expiry settle on read (`expire_if_due` lazy transition)

**File:** `crates/phinbox/src/inbox/mod.rs:236-246` +
`crates/phinbox/src/inbox/expire.rs:11-22`

`expire_if_due` does the in-place `Pending → Expired` transition by
calling `mark_expired_in_place` (which is write+rename, so atomic).
Two concurrent readers can both transition the same expired
request. State is identical, so the semantic loss is zero, but the
audit is incomplete without noting that the second write is also
`fs::write` + `fs::rename` and therefore safe.

## Existing tests (sequential only)

| Test | File | What it covers | Concurrent? |
| --- | --- | --- | --- |
| `http_reanswer_is_refused_and_the_first_answer_stands` | `daemon/tests.rs:305` | Second POST after first | **No** (sequential) |
| `http_routes_return_their_intended_status` | `daemon/tests.rs:262` | Status code per route | No |
| `post_handler_writes_answer` | `daemon/form/tests.rs:18` | Single POST flow | No |
| `expired_request_is_refused_and_not_archived` | `cli/answer.rs:166` | Single CLI answer | No |
| `http_expired_request_is_not_answerable` | `daemon/tests.rs:226` | TTL refusal | No |

## Recommended fix (for a follow-up commit, not this one)

**Option A — per-`request_id` file lock (simplest, POSIX-only)**

Wrap `load` + `expire_if_due` + `finalize` in an exclusive `flock` on
`inbox/{id}.lock`. The lock file is created on first use and held only
for the duration of the answer attempt. Works on macOS/Linux, not
Windows. The Codex bridge in `cli/harness.rs` already uses
`std::fs::OpenOptions::new().create(true).truncate(false)` patterns
that can be extended.

**Option B — CAS in `finalize` (portable)**

Change `finalize` to re-read `inbox/{id}.json` immediately before the
`fs::rename`, refuse if the re-read shows a different `state` than
the caller assumed. This narrows the race window but does not close
it (a third writer can interleave between re-read and rename).

**Option C — single-writer daemon gate**

Send every submit (HTTP, IPC, CLI) through the daemon's HTTP `/inbox/{id}/answer`
endpoint. The CLI binary's `cmd_answer` becomes a thin HTTP client
to `http://127.0.0.1:{port}/inbox/{id}/answer`. The daemon serializes
requests inside a per-`request_id` async mutex. This is the cleanest
fix but requires the CLI to be able to talk to a running daemon, and
preserves the no-daemon case (CLI writes directly via `finalize` when
no daemon is running).

**Option D — concurrent stress test that proves/disproves the race**

Spawn N threads, each calling `submit_answer` / `finalize_via_state` /
`cmd_answer` on the same `request_id`. Assert that exactly one answer
wins and the rest get `AlreadyFinalized` / `BadState`. If the test
passes on the current code, the race is less severe than the analysis
suggests (perhaps the OS-level `flock` semantics or the tokio
scheduler provide implicit serialization). If it fails, we have a
reproducer and a forcing function for the fix.

## Recommendation

Add **Option D** as a follow-up test before any of A/B/C. If the test
fails, implement **Option A** (per-`request_id` `flock`) for the
HTTP and IPC channels, and have the CLI acquire the same lock over
`finalize`. Keep **Option C** as a longer-term refactor.

## Receipt

- No code changes in this audit. Branch HEAD is `4836ac9b` and stays there.
- The `qualify-local.py` live journey (`/tmp/phinbox-live-journey-20261017/local-journey.json`)
  exercised the **sequential** "duplicate answer 409" path
  (check 6 in the receipt), which passes. The audit concludes that
  the sequential invariant is enforced; the concurrent invariant is not.
- For the Codex bridge specifically, the `valid_request_no_answer_deny`
  test in `tests/cli_harness.rs` proves the bridge refuses to act on
  a request that the daemon never answered; that is a different
  invariant from the one audited here.

tx-agent: jcode
tx-validated: race-audit (analysis-only, no code changes; receipts:
  qualify-local.py receipt at /tmp/phinbox-live-journey-20261017/local-journey.json
  shows sequential 409 works; 285/1ignored/0failed cargo test
  shows the audit's referenced test surface is green)
